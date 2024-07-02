import json
from pydantic import BaseModel


class Query(BaseModel):
    text: str
    relevant: bool
    sources: list[str]


def search(query: str) -> list[str]:
    return []


def search_results(query_texts: list[str]) -> list[list]:
    """Returns list of the most related documents by each query"""
    results = []

    for query_text in query_texts:
        docs = search(query_text)
        results.append(docs)

    return results


def evaluate(queries: list[Query], results: list[list]):
    correct = 0

    for query, query_results in zip(queries, results):
        # for unrelevant query nothing should be returned
        if not query["relevant"] and len(query_results) == 0:
            correct += 1

        # for relevant query there should be at least one intersection with the target set
        # {"A", "B"} & {"B", "C"} = {"B"}
        if query["relevant"] and len(set(query["sources"]) & set(query_results)) > 0:
            correct += 1
            # correct += len(set(query['sources']) & set(results))

    accuracy = correct / len(queries)
    return accuracy


def load_queries() -> list[Query]:
    queries = []
    try:
        with open("./validation/queries.jsonl", "r", encoding="utf-8") as file:
            for line in file:
                queries.append(json.loads(line))
    except FileNotFoundError:
        print("Error: File not found.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")

    return queries


if __name__ == "__main__":
    queries = load_queries()
    query_texts = [query["text"] for query in queries]
    results = search_results(query_texts)
    accuracy = evaluate(queries, results)
    print(accuracy)
