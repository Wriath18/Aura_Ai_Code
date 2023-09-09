from config import OPENAI_API_KEY, TEL_API, API_TOKEN, CLIENT_ID, CLIENT_SECRET,REDIRECT_URI
from data_history import conversation_history, user_history_key, user_id_collection, user_id_key, bot_name
from emotion import welcome_message, greeting_list, response_greet, stop_response, stop_words, song_refr, last_conv, name_ask
from transformers import pipeline
import openai, telebot, spotipy, random
import numpy as np
from spotipy import SpotifyOAuth
import time


#sentiment pipeline
sentiment_analyzer = pipeline('sentiment-analysis', model="nlptown/bert-base-multilingual-uncased-sentiment", framework="pt")

#bot settings
openai.api_key = OPENAI_API_KEY
TOKEN = TEL_API
bot = telebot.TeleBot(TOKEN)

class processing:
    def __init__(self, user_input, conversation_history, user_id, message_obj, is_voice):
        self.conversation_history = conversation_history
        self.user_id = user_id
        self.message_obj = message_obj
        self.inputs_count = len(self.conversation_history[user_id][user_history_key])

        if self.inputs_count % 5 == 0 and self.inputs_count > 0:
            self.ask_song_preference()
        else:
            self.process_user_input(user_input)

    def ask_song_preference(self):
        bot.send_message(self.user_id, "You've provided 3 inputs. Would you like a song recommendation? (Yes/No)")
        bot.register_next_step_handler(self.message_obj, self.handle_recommendation_response)

    def handle_recommendation_response(self, message):
        response = message.text.lower()
        if response.startswith("y"):
            user_history = self.conversation_history[self.user_id][user_history_key]
            self.song_recommend(user_history)
        elif response.startswith("n"):
            bot.send_message(self.user_id, "Sure, we can continue to chat. Feel free to ask me anything or let me know when you'd like a song recommendation.")
            self.conversation_history[self.user_id][user_history_key] = [""]
        else:
            bot.send_message(self.user_id, "Please answer with 'Yes' or 'No'.")
            self.ask_song_preference()

    def song_recommend(self, user_history):
        string = " ".join(user_history[-5:])
        result = sentiment_analyzer(string)
        label = result[0]['label']
        score = result[0]['score']
        print(f"Sentence: {string}")
        print(f"Sentiment: {label}, Score: {score}\n")
        if label == "1 star" or label == "2 stars":
            mood = "sad"
        elif label == "3 stars":
            mood = "neutral"
        else:
            mood = "happy"
        response = "\nHere's a playlist that might match your mood:\n"
        song_name = song_processing(mood)
        response += song_name
        bot.send_message(self.user_id, response)
        # Ask if the user likes the song choice
        bot.send_message(self.user_id, f"Do you like this song recommendation? (Yes/No)")
        bot.register_next_step_handler(self.message_obj, self.handle_song_recommendation_response, response)

    def handle_song_recommendation_response(self, message, previous_response):
        response = message.text.lower()
        if response.startswith("y"):
            bot.send_message(self.user_id, "Thank you! Enjoy the music!")
        elif response.startswith("n"):
            # Recommend a new song with the same mood
            mood = self.extract_mood_from_previous_response(previous_response)
            new_song_name = song_processing(mood)
            bot.send_message(self.user_id, f"Here's another song recommendation with the same mood:\n{new_song_name}")
            # Ask if the user likes the new song choice
            bot.send_message(self.user_id, f"Do you like this song recommendation? (Yes/No)")
            bot.register_next_step_handler(self.message_obj, self.handle_song_recommendation_response, new_song_name)
        else:
            bot.send_message(self.user_id, "Please answer with 'Yes' or 'No'.")

    def extract_mood_from_previous_response(self, previous_response):
        if "happy" in previous_response.lower():
            return "happy"
        elif "sad" in previous_response.lower():
            return "sad"
        elif "neutral" in previous_response.lower():
            return "neutral"
        else:
            return "neutral"  # Default mood if not recognized

    def process_user_input(self, user_input):
        response = " "  # Empty initialization
        if any(word in user_input.lower() for word in last_conv):
            last_conversation = "\n".join(self.conversation_history[self.user_id][user_history_key][-5:])
            response = f"Here's a summary of our last conversation:\n{last_conversation}"
        elif any(ask in user_input.lower() for ask in name_ask):
            response = f"\nI am {bot_name}, made by Sanidhya"
        elif any(statement in user_input.lower() for statement in song_refr):
            self.song_recommend(self.conversation_history[self.user_id][user_history_key])
        else:
            user_history = self.conversation_history[self.user_id][user_history_key]
            if len(user_history) >= 5:
                self.ask_song_preference()
            else:
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",  # Use the GPT-3.5 Turbo chat model
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": user_input},
                        ],
                    )
                    response = response.choices[0].message["content"].strip()
                except openai.error.OpenAIError as e:
                    if "Rate limit reached" in str(e):
                        # Handle rate limit exceeded error
                        response = "Request limit of the bot has been crossed. Please wait a few minutes, as this is a free bot with usage limits."
        self.conversation_history[self.user_id][user_history_key].append(user_input)
        self.send_telegram_message(self.message_obj, response)

    def send_telegram_message(self, message_obj, response):
        bot.reply_to(message_obj, response)

def analysis( string):
    result = sentiment_analyzer(string)
    label = result[0]['label']
    score = result[0]['score']
    print(f"Sentence: {string}")
    print(f"Sentiment: {label}, Score: {score}\n")
    if label == "1 star" or label == "2 stars":
        mood = "sad"
    elif label == "3 stars":
        mood = "neutral"
    else:
        mood = "happy"
    response += "\nHere's a playlist that might match your mood:\n"
    song_name = song_processing(mood)


def song_processing(mood_category):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                               client_secret=CLIENT_SECRET,
                                               redirect_uri=REDIRECT_URI,
                                               scope="user-library-read playlist-read-private"))
    playlists = sp.current_user_playlists()
    for playlist in playlists['items']:
        if mood_category in playlist['name'].lower():
            playlist_name = playlist['name'].lower()
            playlist_tracks = sp.playlist_tracks(playlist['id'])
            track_uris = [track['track']['uri'] for track in playlist_tracks['items']]
            chosen_track_uri = random.choice(track_uris)
            chosen_url = (sp.track(chosen_track_uri))['external_urls']['spotify']
            #return f"{playlist['name']} - {playlist['external_urls']['spotify']}\nSong Uri : {chosen_track_uri}\nSong url : {chosen_url}"
            return f"Mood Analysis Result : {mood_category}\nSong url : {chosen_url}"
            
    
    return "Sorry, no matching playlist found."


###Handeling telegram responses
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_id_collection.append(user_id)  # Add user ID to the collection
    try:
        conversation_history[user_id] = {
            user_history_key: [],
            user_id_key: user_id,
        }
        response = f"\n Your id: {user_id} \n"
        response += random.choice(response_greet)
        bot.send_message(user_id, welcome_message)
        bot.reply_to(message, response)

    except Exception as e:
        print(f"An error occured {e}")
        bot.send_message(user_id, "Sorry, Something went wrong !! \n\nPlease write /stop and then /start to continue with new session")


@bot.message_handler(commands=['stop'])
def start(message):
    user_id = message.chat.id
    try:
        response = f"\n Your id: {user_id} \n"
        response += random.choice(stop_response)
        bot.reply_to(message, response)
        if user_id in conversation_history:
            del conversation_history[user_id]
    
    except Exception as e:
        print(f"An error occured {e}")
        bot.send_message(user_id, "Sorry, Something went wrong !! \n\nPlease write /stop and then /start to continue with new session")


@bot.message_handler(func=lambda message: True)
def message_handler(message):
    user_message = message.text
    user_id = message.chat.id

    # Check if the user explicitly requests a song recommendation
    if "recommend a song" in user_message.lower():
        user_history = conversation_history[user_id][user_history_key]
        process = processing("Yes", conversation_history, user_id, message, False)  # Trigger the song recommendation
    else:
        try:
            if user_id not in user_id_collection:
                start(message)
            user_history = conversation_history[user_id][user_history_key]
            process = processing(user_message, conversation_history, user_id, message, False)
        except Exception as e:
            print(f"An error occurred {e}")
            bot.send_message(user_id, "Sorry, something went wrong! Please write /stop and then /start to continue with a new session")


#report
@bot.message_handler(commands=['feedback'])
def feedback(message):
    user_id = message.chat.id
    if user_id not in user_id_collection:
        bot.reply_to(user_id, "Please first start a chat session by typing /start")
    else:
        bot.reply_to(user_id, "Please provide your feedback:")
        #bot.register_next_step_handler(message, process_feedback)

def process_feedback(message):
    user_id = message.chat.id
    feedback_text = message.text
    feedback_channel_id = 'aura_feedbacks'
    bot.send_message(feedback_channel_id, f"Feedback from user {user_id}:\n{feedback_text}")
    
    # Notify the user that their feedback has been received
    bot.send_message(user_id, "Thank you for your feedback!")
    if user_id in conversation_history:
        del conversation_history[user_id]



if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)  # Sleep for 10 seconds before retrying

