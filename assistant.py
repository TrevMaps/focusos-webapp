try:
    import pyttsx3
    engine = pyttsx3.init()
except:
    engine = None

def speak(text):
    if engine:
        engine.say(text)
        engine.runAndWait()
    else:
        print(text)

import openai

openai.api_key = "YOUR_API_KEY"

def ask_ai(question):

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":question}]
    )

    return response["choices"][0]["message"]["content"]