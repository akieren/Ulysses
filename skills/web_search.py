import requests

from memory.config_manager import get_url

TAVILY_API_KEY = "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"


def summarize_with_llm(query: str, search_context: str) -> str:
    url = get_url()

    prompt = (
        f"You are Ulysses, a highly intelligent and charismatic AI assistant. "
        f"The user asked to search for: '{query}'. "
        f"Based ONLY on the following clean search data, provide a brief, accurate, and spoken-style summary (1-3 sentences). "
        f"Address the user as 'Sir'.\n\nSearch Data:\n{search_context}"
    )

    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are Ulysses. Summarize information concisely, elegantly, and without markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    try:
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"\033[31m[ERROR] LLM Summarization failed: {e}\033[0m")

    return "Sir, I found the information, but my cognitive processor couldn't summarize it right now."


def perform_search(parameters: dict, response: str, client_instance) -> bool:
    temp_mem = client_instance.temp_memory

    if parameters:
        temp_mem.update_parameters(parameters)

    query = temp_mem.parameters.get("query")

    if not query:
        temp_mem.pending_intent = "search"
        client_instance.speak("Sir, what exactly would you like me to look up?")
        return False

    if response and len(response) > 5:
        client_instance.speak(response)

    print(f"\n\033[36m[WEB SEARCH] Looking up: '{query}' via Tavily...\033[0m")

    try:
        api_url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_answer": True,
            "max_results": 3,
        }
        res = requests.post(api_url, json=payload, timeout=15)
        data = res.json()

        # Tavily'den gelen veriyi derliyoruz
        tavily_answer = data.get("answer", "")
        snippets = [result["content"] for result in data.get("results", [])]

        if tavily_answer:
            context = tavily_answer
        elif snippets:
            context = " ".join(snippets)
        else:
            client_instance.speak(
                "Sir, I couldn't find any relevant information on that topic."
            )
            temp_mem.pending_intent = None
            temp_mem.parameters = {}
            return False

    except Exception as e:
        print(f"\033[31m[ERROR] Web Search Failed: {e}\033[0m")
        client_instance.speak("Sir, I couldn't connect to the global network.")
        temp_mem.pending_intent = None
        temp_mem.parameters = {}
        return False

    print(f"\033[35m[SYSTEM] Summarizing search results via Local Brain...\033[0m")
    final_answer = summarize_with_llm(query, context)

    temp_mem.pending_intent = None
    temp_mem.parameters = {}

    print(f"\033[32m[SYSTEM] Search complete. Reading results.\033[0m")
    client_instance.addToHistory(final_answer, "assistant")

    client_instance.speak(final_answer)
    return True
