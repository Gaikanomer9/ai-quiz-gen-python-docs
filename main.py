from html.parser import HTMLParser
import json
import requests
import openai
import os
import random
import re

base_url = "https://docs.python.org/3/library/"
docs_url = "https://docs.python.org/3/library/index.html"
openai.api_key = os.getenv("OPENAI_API_KEY")


class ContentParser(HTMLParser):
    content = []
    current_content = ""
    current_tag = ""

    headers_to_ignore = ["Table of Contents",
                         "Report a Bug", "index", "Show Source",
                         "Previous topic", "Next topic", "This Page", "Navigation", "Python 3.11.3 documentation"]

    header_tags = ["h1", "h2", "h3", "h4", "h5", "h6"]

    def __init__(self):
        super().__init__()
        self.content = []
        self.current_content = ""
        self.current_tag = ""

    def handle_starttag(self, tag, attrs):
        if tag in self.header_tags:
            if self.current_tag == "":
                self.current_tag = tag
                self.content.append(self.current_content)
                self.current_content = ""
                return

    def handle_data(self, data):
        self.current_content += data

    def handle_endtag(self, tag):
        if tag == self.current_tag:
            self.current_tag = ""
            return


class LinksParser(HTMLParser):
    links = []
    link_found = False

    def handle_starttag(self, tag, attrs):
        if tag.startswith("a"):
            self.link_found = True
            internal_link = False
            for attr in attrs:
                if attr[0] == 'class' and attr[1] == 'reference internal':
                    internal_link = True
                    break
            if internal_link:
                for attr in attrs:
                    if attr[0] == 'href':
                        self.links.append(base_url + attr[1])
                        break


def extract_links(url):
    content = requests.get(url).content
    parser = LinksParser()
    parser.feed(content.decode("utf-8"))
    return parser.links


def parse_page(url):
    content = requests.get(url).content
    parser = ContentParser()
    parser.feed(content.decode("utf-8"))
    parser.content = list([re.sub('\\n', '', x) for x in parser.content])
    parser.content = list([re.sub('\s+', ' ', x) for x in parser.content])

    parser.content = list(filter(
        lambda x: not any([title in x for title in parser.headers_to_ignore]), parser.content))
    return parser.content


def send_message(messages: list):
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages)
    try:
        content = resp.choices[0]["message"]["content"]
    except Exception as e:
        print(e)
        content = ""
    return content


def generate_quiz():
    random_link = doc_links[random.randint(0, len(doc_links) - 1)]
    content = parse_page(random_link)
    random_content = content[random.randint(0, len(content) - 1)]
    messages_to_send = messages.copy()
    messages_to_send.append(
        {"role": "system", "content": f"Generate quiz question and answers for the following: {random_content}"})
    quiz_json_string = send_message(messages_to_send)
    quiz = json.loads(quiz_json_string.replace("\n", ""))
    return quiz, random_link


messages = [
    {"role": "system", "content": "You are a quiz Master and Python Expert."},
    {"role": "system", "content": 
    "You will receive a piece of Python documentation and you will generate a question based on it."},
    {"role": "system", "content": 
    "You will also generate 4 answers, one of which is correct."},
    {"role": "system", "content": 
    "Provide everything in a json format with keys: question and options, options have keys answer and correct. \
    Return your answer wraped in a json object without remarks."},
]

doc_links = extract_links(docs_url)


if __name__ == "__main__":
    continue_game = True
    print("Welcome to the Python Quiz Game! 🐍")
    print("You will receive a random question from the Python doc, try to answer it correctly ✅.")
    points = 0
    rounds = 0
    while continue_game:
        print("Generating a question...")
        quiz, random_link = generate_quiz()
        print(f"Question: {quiz.get('question')} from {random_link}")
        for i, item in enumerate(quiz.get("options")):
            print(f"{i+1}. {item.get('answer')}")
        print("Choose an answer (1-4): or enter 0 to skip")
        user_answer = input("Your answer: ")
        if user_answer == "0":
            print("Skipping...")
            continue
        if quiz.get("options")[int(user_answer) - 1].get("correct"):
            print("Correct! 🎉")
            points += 1
        else:
            print("Wrong! 😢")
            print("The correct answer is: ")
            for i, item in enumerate(quiz.get("options")):
                if item.get("correct"):
                    print(f"{i+1}. {item.get('answer')}")
        rounds += 1
        continue_game = input("Do you want to continue? (y/n) ") == "y"
    print(f"Your score is: {points}/{rounds} 🎉")
