"""Retrieve Tweets, embeddings, and persist in the database."""
from os import getenv
import os
from dotenv import load_dotenv
import basilica
import tweepy
from .models import DB, Tweet, User



load_dotenv()

TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY", default="OOPS")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET", default="OOPS")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", default="OOPS")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", default="OOPS")
BASILICA_API_KEY = os.getenv("BASILICA_API_KEY", default="OOPS")

def twitter_api_client():
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    print(type(auth))
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
    client = tweepy.API(auth)
    return client

def basilica_connection():
    connection = basilica.Connection(BASILICA_API_KEY)
    print(connection)
    return connection

client = twitter_api_client()
basilica_client = basilica_connection()



# https://greatist.com/happiness/must-follow-twitter-accounts
TWITTER_USERS = ['elonmusk', 'conanobrien'
                 ]

TWITTER_AUTH = tweepy.OAuthHandler(getenv('TWITTER_CONSUMER_KEY'),
                                   getenv('TWITTER_CONSUMER_SECRET'))
TWITTER_AUTH.set_access_token(getenv('TWITTER_ACCESS_TOKEN'),
                              getenv('TWITTER_ACCESS_TOKEN_SECRET'))
TWITTER = tweepy.API(TWITTER_AUTH)
BASILICA = basilica.Connection(getenv('BASILICA_KEY'))


def add_or_update_user(username):
    """Add or update a user and their Tweets, error if not a Twitter user."""
    try:
        twitter_user = TWITTER.get_user(username)
        db_user = (User.query.get(twitter_user.id) or
                   User(id=twitter_user.id, name=username))
        DB.session.add(db_user)
        # We want as many recent non-retweet/reply statuses as we can get
        # 200 is a Twitter API limit, we'll usually see less due to exclusions
        tweets = twitter_user.timeline(
            count=100, exclude_replies=True, include_rts=False,
            tweet_mode='extended', since_id=db_user.newest_tweet_id)
        if tweets:
            db_user.newest_tweet_id = tweets[0].id
        for tweet in tweets:
            # Calculate embedding on the full tweet, but truncate for storing
            embedding = BASILICA.embed_sentence(tweet.full_text,
                                                model='twitter')
            db_tweet = Tweet(id=tweet.id, text=tweet.full_text[:300],
                             embedding=embedding)
            db_user.tweets.append(db_tweet)
            DB.session.add(db_tweet)
    except Exception as e:
        print('Error processing {}: {}'.format(username, e))
        raise e
    else:
        DB.session.commit()


def add_users(users=TWITTER_USERS):
    """
    Add/update a list of users (strings of user names).
    May take awhile, so run "offline" (flask shell).
    """
    for user in users:
        add_or_update_user(user)


def update_all_users():
    """Update all Tweets for all Users in the User table."""
    for user in User.query.all():
        add_or_update_user(user.name)
