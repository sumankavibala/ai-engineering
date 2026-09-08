def evaluate_retrieval(
  retrieved_chunks,
  expected_source
):
  if expected_source is None:
    return len(retrieved_chunks) == 0

  return any(
    chunk.source == expected_source
    for chunk in retrieved_chunks
  )