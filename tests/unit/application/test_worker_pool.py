import threading

from prismic.application.worker_pool import WorkerPool


def test_submit_runs_the_function_and_returns_its_result() -> None:
    pool = WorkerPool()
    try:
        future = pool.submit(lambda a, b: a + b, 2, 3)
        assert future.result(timeout=5) == 5
    finally:
        pool.shutdown()


def test_submit_runs_off_the_calling_thread() -> None:
    pool = WorkerPool()
    try:
        future = pool.submit(threading.get_ident)
        worker_thread_id = future.result(timeout=5)
        assert worker_thread_id != threading.get_ident()
    finally:
        pool.shutdown()


def test_context_manager_shuts_down_on_exit() -> None:
    with WorkerPool() as pool:
        future = pool.submit(lambda: "done")
        assert future.result(timeout=5) == "done"
    # The executor is shut down; submitting after exit raises.
    try:
        pool.submit(lambda: None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected submit() after shutdown to raise")
