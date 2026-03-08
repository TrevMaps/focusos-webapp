import pyttsx3

engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

import openai

openai.api_key = "YOUR_API_KEY"

def ask_ai(question):

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role":"user","content":question}]
    )

    return response["choices"][0]["message"]["content"]