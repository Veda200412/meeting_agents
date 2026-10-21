import os
from unittest.mock import patch

from app.api import routes


def test_vercel_workflow_runs_in_request_process():
    db = object()
    with patch.dict(os.environ, {"VERCEL": "1"}), patch.object(
        routes, "execute_workflow"
    ) as execute, patch.object(routes.threading, "Thread") as thread:
        routes._launch_workflow("run-1", db)

    execute.assert_called_once_with("run-1", db)
    thread.assert_not_called()


def test_vercel_resume_runs_in_request_process():
    db = object()
    with patch.dict(os.environ, {"VERCEL": "1"}), patch.object(
        routes, "resume_workflow"
    ) as resume, patch.object(routes.threading, "Thread") as thread:
        routes._launch_workflow("run-1", db, resume=True)

    resume.assert_called_once_with("run-1", db)
    thread.assert_not_called()
