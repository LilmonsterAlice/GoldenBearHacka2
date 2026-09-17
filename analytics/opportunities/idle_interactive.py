"""Recompute official idle-session eligibility; not a timeout simulation."""


def idle_candidates(jobs):
    required = {"job_type", "walltime_sec", "sm_util_avg", "gpu_hours", "id_job"}
    if not required.issubset(jobs.columns):
        raise ValueError(f"Missing idle-session columns: {sorted(required - set(jobs.columns))}")
    eligible = (jobs.job_type.eq("LLSUB:INTERACTIVE") &
                jobs.walltime_sec.gt(4 * 3600) & jobs.sm_util_avg.lt(5))
    return jobs.loc[eligible].sort_values(["gpu_hours", "id_job"], ascending=[False, True]).copy()
