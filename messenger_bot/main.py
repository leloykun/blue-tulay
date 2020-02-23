import random
import time
import hashlib
from flask import Flask, request
from pymessenger.bot import Bot
from google.cloud import storage

app = Flask(__name__)
ACCESS_TOKEN = 'EAAHUZB2qKO78BANHbqf3MqWweYNoRe6f1BeNFNoS4LMZBN5rZAvbZBQ1hADYlA5ggzZAete52pvPYkZCebUdT2Xa72frKekEsykjD3ykl3F9RI9TxPIM7qPK99AFY5ZBkYy5E2JCBnWz9gAy33ABRBtmeDwY6JsHYUFGM2mw2dagKbZC2Xnq084i'
VERIFY_TOKEN = 'TULAY-TOKEN'
bot = Bot(ACCESS_TOKEN)


def get_contents(filename):
    client = storage.Client()
    bucket = client.get_bucket('database-tulay')
    blob = bucket.get_blob(filename)
    return blob.download_as_string().decode()


def save_contents(filename, contents):
    client = storage.Client()
    bucket = client.get_bucket('database-tulay')
    blob = bucket.get_blob(filename)
    blob.upload_from_string(contents)


def get_dict(filename, to_int=False):
    dict_raw = get_contents(filename)
    user_data = {}
    for line in dict_raw.strip().split('\n'):
        if to_int:
            user_id, state = list(map(int, line.split('||')))
        else:
            user_id, state = line.split('||')
        user_data[user_id] = state
    print(filename, user_data)
    return user_data


def save_dict(user_states, filename='states.txt'):
    contents = ""
    for user_id in user_states:
        contents += str(user_id) + "||" + str(user_states[user_id]) + "\n";
    save_contents(filename, contents)

#We will receive messages that Facebook sends our bot at this endpoint
@app.route("/", methods=['GET', 'POST'])
def receive_message():
    if request.method == 'GET':
        """Before allowing people to message your bot, Facebook has implemented a verify token
        that confirms all requests that your bot receives came from Facebook."""
        token_sent = request.args.get("hub.verify_token")
        return verify_fb_token(token_sent)
    #if the request was not get, it must be POST and we can just proceed with sending a message back to user
    else:
        # CAREFUL WHEN UPLOADING FILES!!

        output = request.get_json()
        for event in output['entry']:
            messaging = event['messaging']
            for message in messaging:
                print(message)

                user_states = get_dict('states.txt', True)

                recipient_id = int(message['sender']['id'])
                if recipient_id not in user_states:
                    user_states[recipient_id] = 0

                time.sleep(0.3)

                if user_states[recipient_id] == 0 and message.get('message'):
                    user_states[recipient_id] = 1;
                    save_dict(user_states)

                    text = "If you want to ask for something about our country, play a quiz game, or book a tour, just press the corresponding button below:"
                    buttons = [{
                        "type" : "postback",
                        "title" : "Ask",
                        "payload" : "ask"
                    }, {
                        "type" : "postback",
                        "title" : "Play",
                        "payload" : "play"
                    }, {
                        "type":"web_url",
                        "url":"https://www.figma.com/proto/47UGOufBkCJ16NK3fjSiDz/Tulay?node-id=20%3A2&scaling=scale-down",
                        "title":"Explore"
                    }]
                    bot.send_button_message(recipient_id,
                                            text,
                                            buttons);
                elif user_states[recipient_id] == 1 and message.get('postback'):
                    payload = message['postback']['payload']
                    if payload == 'ask':
                        user_states[recipient_id] = 2;
                        save_dict(user_states)

                        bot.send_text_message(recipient_id, "What do you want to ask?")
                    elif payload == 'play':
                        user_states[recipient_id] = 3;
                        save_dict(user_states)

                        question = find_question()

                        bot.send_text_message(recipient_id, question)
                elif user_states[recipient_id] == 2 and message.get('message'):
                    if message['message'].get('text'):
                        question = message['message'].get('text')
                        answer = get_answer(question)
                        if answer == "NO_ANSWER":
                            answer = "I'm sorry, we don't have information for that yet. But we'll get back to you when we get it :)"
                        bot.send_text_message(recipient_id, answer)

                    #if user sends us a GIF, photo,video, or any other non-text item
                    if message['message'].get('attachments'):
                        image_url = message['message'].get('attachments')[0]['payload']['url']
                        detected = identify_image(image_url)
                        if detected == "NOT_DECTECTED":
                            detected = "I'm sorry, but we can't recognize that image. Please try again later."
                        bot.send_text_message(recipient_id, "I think it's " + detected)

                    text = "Do you want to ask more questions?"
                    buttons = [{
                        "type" : "postback",
                        "title" : "Yes",
                        "payload" : "ask_more"
                    }, {
                        "type" : "postback",
                        "title" : "No",
                        "payload" : "ask_no_more"
                    }]
                    bot.send_button_message(recipient_id,
                                            text,
                                            buttons);
                elif user_states[recipient_id] == 2 and message.get('postback'):
                    payload = message['postback']['payload']
                    if payload == 'ask_more':
                        bot.send_text_message(recipient_id, "What else do you want to ask?")
                    elif payload == 'ask_no_more':
                        user_states[recipient_id] = 0
                        save_dict(user_states)

                        bot.send_text_message(recipient_id, "Thanks for asking around!")
                elif user_states[recipient_id] == 3 and message.get('message'):
                    if message['message'].get('text'):
                        question = find_question()
                        answer = message['message'].get('text')

                        question_answer = get_dict('question-answer.txt')
                        question_answer[question] = answer
                        time.sleep(0.3)
                        save_dict(question_answer, 'question-answer.txt')

                        bot.send_text_message(recipient_id, "That's correct!")

                    text = "Do you want to ask more tests?"
                    buttons = [{
                        "type" : "postback",
                        "title" : "Yes",
                        "payload" : "test_more"
                    }, {
                        "type" : "postback",
                        "title" : "No",
                        "payload" : "test_no_more"
                    }]
                    bot.send_button_message(recipient_id,
                                            text,
                                            buttons);
                elif user_states[recipient_id] == 3 and message.get('postback'):
                    payload = message['postback']['payload']
                    if payload == 'test_more' or payload == 'test_no_more':
                        user_states[recipient_id] = 0
                        save_dict(user_states)

                        bot.send_text_message(recipient_id, "Thanks for playing!")

    return "Message Processed"


def verify_fb_token(token_sent):
    #take token sent by facebook and verify it matches the verify token you sent
    #if they match, allow the request, else return an error
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'

def identify_image(image_url):
    image_label = get_dict('image-labels.txt')
    if image_url in image_label:
        return image_label[image_url]

    image_label[image_url] = "NOT_DECTECTED";
    time.sleep(0.3)
    save_dict(image_label, 'image-labels.txt')

    return image_label[image_url]

def get_answer(question, is_image=False):
    question_answer = get_dict('question-answer.txt')
    if question in question_answer:
        return question_answer[question]

    question_answer[question] = "NO_ANSWER"
    time.sleep(0.3)
    save_dict(question_answer, 'question-answer.txt')

    return question_answer[question]

def find_question():
    question_answer = get_dict('question-answer.txt')
    for question in question_answer:
        if question_answer[question] == "NO_ANSWER":
            return question
    return "Translate 'Pang-ilang pangulo ng Pilipinas si Duterte?' to English"

if __name__ == "__main__":
    app.run()
