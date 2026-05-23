# Prompt Structure

These files are the canonical prompt documentation for the FastBid24 extraction pipeline.

The current browser app intentionally keeps the runtime prompt strings inside `app.jsx` because it is a zero-build static app loaded directly by `index.html`. That preserves the existing extraction behavior and avoids changing the LLM flow while the backend is introduced.

Recommended migration path when this becomes a bundled frontend/backend app:

1. Move runtime prompt text into versioned files under this folder.
2. Add a prompt manifest with prompt IDs, versions, model constraints, and expected output schema.
3. Load prompts through a typed frontend service or backend extraction service.
4. Store `prompt_id` and `prompt_version` on every `pdf_runs` row for auditability.

Do not edit these prompt files independently from the matching prompt text in `app.jsx` until that migration is done.
