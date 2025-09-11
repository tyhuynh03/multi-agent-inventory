try:
	from langsmith.run_helpers import traceable  # type: ignore
except Exception:  # fallback khi không cài LangSmith
	def traceable(*args, **kwargs):  # type: ignore
		def decorator(fn):
			return fn
		return decorator
