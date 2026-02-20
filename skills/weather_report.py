import requests

API_KEY = "3c1d3d2eac9e87869c3cd8ffa4b117b6"


def get_weather(parameters: dict, response: str, client_instance) -> bool:
    city = parameters.get("city")

    if not city:
        memory = client_instance.long_term_memory
        city = memory.get("identity", {}).get("city")

    if not city:
        client_instance.temp_memory.pending_intent = "weather_report"
        question = "Sir, I don't have your city on record. For which city would you like the weather report?"
        client_instance.addToHistory(question, "assistant")
        client_instance.speak(question)
        return False

    if response and len(response) > 5:
        client_instance.speak(response)

    print(
        f"\033[36m[WEATHER] Fetching precise meteorological data for {city}...\033[0m"
    )

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        res = requests.get(url, timeout=10)
        data = res.json()

        if res.status_code == 200:
            current_temp = round(data["main"]["temp"])
            condition = data["weather"][0]["description"]

            weather_text = f"Sir, currently in {city}, the weather is {condition} with a temperature of {current_temp} degrees Celsius."

            print(f"\033[32m[SYSTEM] {weather_text}\033[0m")

            client_instance.addToHistory(weather_text, "assistant")
            client_instance.speak(weather_text)
            return True
        else:
            error_msg = (
                f"Sir, I couldn't find the exact meteorological data for {city}."
            )
            print(f"\033[31m[ERROR] OWM Error: {data.get('message')}\033[0m")
            client_instance.addToHistory(error_msg, "assistant")
            client_instance.speak(error_msg)
            return False

    except requests.exceptions.RequestException as e:
        error_msg = "Sir, I am unable to connect to the meteorological servers."
        print(f"\033[31m[ERROR] Weather API Connection Failed: {e}\033[0m")
        client_instance.addToHistory(error_msg, "assistant")
        client_instance.speak(error_msg)
        return False
