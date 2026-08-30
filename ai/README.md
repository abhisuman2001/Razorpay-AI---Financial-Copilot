# Local AI seam

The prototype intentionally has no LLM dependency. `backend/services/ai.py` owns the provider contract and returns deterministic, explainable recommendations today. A local Ollama adapter can be added later without moving financial calculations into the model.