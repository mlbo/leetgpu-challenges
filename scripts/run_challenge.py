#!/usr/bin/env python3
import argparse
import ctypes
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import torch
import websocket

SERVICE_URL = os.getenv("SERVICE_URL", "http://localhost:8080")
LEETGPU_API_KEY = os.getenv("LEETGPU_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def find_solution_file(challenge_dir: Path, language: str) -> Path:
    language_to_extension = {
        "cuda": "cu",
        "mojo": "mojo",
        "pytorch": "py",
        "cute": "py",
        "triton": "py",
        "jax": "py",
    }
    ext = language_to_extension[language]
    
    # 1. Check Testing/solution.ext
    solution_file = challenge_dir / "Testing" / f"solution.{ext}"
    if solution_file.exists():
        return solution_file
        
    # 2. Check current directory for solution.ext
    local_solution = Path(f"solution.{ext}")
    if local_solution.exists():
        return local_solution

    # 3. Fallback to starter if solution doesn't exist
    starter_file = challenge_dir / "starter" / f"starter.{ext}"
    if starter_file.exists():
        return starter_file
    
    raise FileNotFoundError(
        f"No solution or starter file found for {language}. "
    )


def get_gpu_arch():
    """Get the local GPU compute capability and return the appropriate nvcc arch flag."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True
        )
        cap = result.stdout.strip().replace(".", "")
        if cap:
            return f"-arch=sm_{cap}"
    except Exception:
        pass
    return "-arch=sm_75"  # Fallback to T4 architecture


def compile_cuda(solution_path: Path, output_dir: Path = None) -> Path:
    """Compile CUDA solution to a shared library."""
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        so_path = output_dir / f"{solution_path.stem}.so"
    else:
        with tempfile.NamedTemporaryFile(suffix=".so", delete=False) as tmp:
            so_path = Path(tmp.name)
    
    arch_flag = get_gpu_arch()
    cmd = [
        "nvcc",
        "-O3",
        arch_flag,
        "-Xcompiler",
        "-fPIC",
        "--shared",
        str(solution_path),
        "-o",
        str(so_path),
        "-lcublas",
        "-lcurand",
    ]
    logger.info("Compiling CUDA: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Compilation failed:\n%s", result.stderr)
        if not output_dir and so_path.exists():
            so_path.unlink()
        sys.exit(1)
    return so_path


def run_local_tests(challenge_path: Path, language: str, solution_path: Path, output_dir: Path = None):
    """Run tests locally using the reference implementation and the solution."""
    # Add challenge_path to sys.path to import Challenge
    sys.path.append(str(challenge_path.parent.parent)) # challenges/
    sys.path.append(str(challenge_path)) # challenge_dir/
    
    try:
        from challenge import Challenge
    except ImportError as e:
        logger.error("Failed to import Challenge from %s: %s", challenge_path, e)
        return False

    challenge = Challenge()
    
    so_path = None
    if language == "cuda":
        so_path = compile_cuda(solution_path, output_dir)
        lib = ctypes.CDLL(str(so_path))
        solve_func = lib.solve
        
        # Setup argument types based on signature
        signature = challenge.get_solve_signature()
        argtypes = []
        arg_names = []
        for name, (ctype, direction) in signature.items():
            argtypes.append(ctype)
            arg_names.append(name)
        solve_func.argtypes = argtypes
        
        def run_solve(**kwargs):
            args = []
            for name in arg_names:
                val = kwargs[name]
                if isinstance(val, torch.Tensor):
                    # Get pointer to data
                    ptr = ctypes.cast(val.data_ptr(), signature[name][0])
                    args.append(ptr)
                else:
                    args.append(val)
            solve_func(*args)
            torch.cuda.synchronize()

    else:
        logger.error("Local run only supported for 'cuda' currently.")
        return False

    test_cases = [challenge.generate_example_test()] + challenge.generate_functional_test()
    
    all_passed = True
    for i, test_case in enumerate(test_cases):
        logger.info("Running test case %d...", i)
        
        # Prepare inputs for reference and solution
        ref_inputs = {k: v.clone() if isinstance(v, torch.Tensor) else v for k, v in test_case.items()}
        sol_inputs = {k: v.clone() if isinstance(v, torch.Tensor) else v for k, v in test_case.items()}
        
        # Run reference
        challenge.reference_impl(**ref_inputs)
        
        # Run solution
        try:
            run_solve(**sol_inputs)
        except Exception as e:
            logger.error("Test case %d failed with error: %s", i, e)
            all_passed = False
            continue

        # Compare outputs
        signature = challenge.get_solve_signature()
        for name, (_, direction) in signature.items():
            if direction in ["out", "inout"]:
                ref_out = ref_inputs[name]
                sol_out = sol_inputs[name]
                if not torch.allclose(ref_out, sol_out, atol=challenge.atol, rtol=challenge.rtol):
                    logger.error("Test case %d failed: %s mismatch", i, name)
                    all_passed = False
                else:
                    logger.info("Test case %d: %s passed", i, name)

    if not output_dir and so_path and so_path.exists():
        so_path.unlink()
        
    return all_passed


def submit_solution(
    ws_url: str,
    api_key: str,
    challenge_code: str,
    file_name: str,
    content: str,
    language: str,
    gpu: str,
    action: str,
    public: bool,
) -> bool:

    ws = websocket.create_connection(ws_url, timeout=120)
    try:
        submission = {
            "action": action,
            "token": api_key,
            "submission": {
                "files": [{"name": file_name, "content": content}],
                "language": language,
                "gpu": gpu,
                "mode": "accelerated",
                "public": public,
                "challengeCode": challenge_code,
            },
        }
        ws.send(json.dumps(submission))
        logger.info("Submitted %s", file_name)

        while True:
            msg = ws.recv()
            if not msg:
                continue
            data = json.loads(msg)
            status = data.get("status")
            output = data.get("output")
            logger.info("Status: %s | Output: %s", status, output)
            if status in {"success", "error", "timeout", "oom", "interrupted"}:
                return status == "success"
    finally:
        ws.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit a solution via WebSocket API.")
    parser.add_argument("challenge_path", type=Path, help="Path to the challenge directory")
    parser.add_argument("--language", default="cuda", help="Language (default: cuda)")
    parser.add_argument(
        "--gpu", default="NVIDIA TESLA T4", help="GPU name (default: NVIDIA TESLA T4)"
    )
    parser.add_argument(
        "--action", default="run", choices=["run", "submit"], help="Action (run or submit)"
    )
    parser.add_argument(
        "--local", action="store_true", help="Run tests locally (no API key required)"
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Directory to store local compilation artifacts"
    )
    parser.add_argument(
        "--solution", type=Path, help="Path to the solution file (optional)"
    )
    args = parser.parse_args()

    challenge_py = args.challenge_path / "challenge.py"
    if not challenge_py.exists():
        logger.error("No challenge.py found in %s", args.challenge_path)
        return 1
    
    # Check for API key if not local
    if not args.local and not LEETGPU_API_KEY:
        logger.error("LEETGPU_API_KEY environment variable is required for remote submission")
        return 1

    try:
        if args.solution:
            solution_path = args.solution
        else:
            solution_path = find_solution_file(args.challenge_path, args.language)
        
        if not solution_path.exists():
            raise FileNotFoundError(f"Solution file not found: {solution_path}")
            
        file_name = solution_path.name
        content = solution_path.read_text()
    except Exception as e:
        logger.error("Failed to find solution file: %s", e)
        return 1

    if args.local:
        ok = run_local_tests(args.challenge_path, args.language, solution_path, args.output_dir)
        return 0 if ok else 1

    challenge_code = challenge_py.read_text()
    # Convert http(s) URL to ws(s) URL
    ws_url = SERVICE_URL.replace("https://", "wss://").replace("http://", "ws://")
    ok = submit_solution(
        ws_url=f"{ws_url.rstrip('/')}/api/v1/ws/submit",
        api_key=LEETGPU_API_KEY,
        challenge_code=challenge_code,
        file_name=file_name,
        content=content,
        language=args.language,
        gpu=args.gpu,
        action=args.action,
        public=False,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
