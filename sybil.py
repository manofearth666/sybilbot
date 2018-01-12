import time
import sys
import logging
from random import shuffle

import telepot
from telepot.loop import MessageLoop
from telepot.delegate import pave_event_space, per_from_id, create_open, per_chat_id

from tarotdeck import TarotDeck
from logconfig import setup_logger

import redis


class Sybil(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(Sybil, self).__init__(*args, **kwargs)
        self.deck = {}
        self.decks = {}
        self.from_id = 0
        temp_deck = TarotDeck('crowleythoth')
        self.deck_ref = temp_deck.deckRef

    def majors(self):
        self.sender.sendMessage('Setting your deck to Majors only')
        logging.info('Setting deck to Majors')
        self.deck['deck_object'] = TarotDeck(self.deck['type'])[57:]

    def minors(self):
        self.sender.sendMessage('Setting your deck to Minors only')
        logging.info('Setting deck to Minors')
        self.deck['deck_object'] = TarotDeck(self.deck['type'])[:56]

    def full_deck(self):
        self.sender.sendMessage('Setting your deck to both Majors and Minors')
        logging.info('Setting Majors and Minors')
        self.deck['deck_object'] = TarotDeck(self.deck['type'])

    def set_deck(self):
        if self.deck['composition'] == 'majors':
            self.majors()
        elif self.deck['composition'] == 'minors':
            self.minors()
        else:
            self.full_deck()
        logging.info('shuffling deck')
        shuffle(self.deck['deck_object'])

    def on_chat_message(self, message):
        content_type, chat_type, chat_id = telepot.glance(message)
        from_id = message['from']['id']
        if chat_type == 'group':
            sender = '{0} in {1}'.format(message['from']['username'], message['chat']['title'])
        else:
            sender = '{0} in a private message'.format(message['from']['username'])

        sender += ', chat_id {0}'.format(chat_id)

        if not redis.get(from_id):
            logging.info('initializing deck for {}'.format(sender))
            self.deck = {'type': 'crowleythoth', 'composition': 'full_deck', 'deck_object': TarotDeck('crowleythoth')}
            redis.set(from_id, 'crowleythoth')
            self.deck['deck_object'] = TarotDeck(self.deck['type'])
            shuffle(self.deck['deck_object'])
            #logging.info('Current decks: {}'.format(self.decks))
        else:
            logging.info('redis deck for {} is {}'.format(from_id, redis.get(from_id)))
            deck_type = redis.get(from_id)
            self.deck = self.deck = {'type': deck_type, 'composition': 'full_deck', 'deck_object': TarotDeck(deck_type)}
            shuffle(self.deck['deck_object'])

        if content_type == 'text':
            logging.info('Message from {}'.format(sender))
            logging.info('Message Body: {}'.format(message['text']))
            
            message_text = message['text']
            message_lower = message_text.lower()
            command_tokens = message_lower.split()
            
            if command_tokens[0] in ('/majors', '/majors@sybilforkbot'): 
                self.deck['composition'] = 'majors'
                self.set_deck()

            elif command_tokens[0] in ('/minors', '/minors@sybilforkbot'):
                self.deck['composition'] = 'minors'
                self.set_deck()
            
            elif command_tokens[0] in ('/full', '/full@sybilforkbot'):
                self.deck['composition'] = 'full_deck'
                self.set_deck()
            
            elif command_tokens[0] in ('/shuffle', '/shuffle@sybilforkbot'):
                self.set_deck()
                self.sender.sendMessage('Shuffling the deck...')
            
            elif command_tokens[0] in ('/settype', '/settype@sybilforkbot'):
                
                if command_tokens[1] not in self.deck_ref.keys():
                    logging.info('{} requested an invalid deck'.format(sender))
                    self.sender.sendMessage('Invalid deck type')
                else:
                    logging.info('deck switch reqest to {}, command_tokens: {}'.format(self.deck, command_tokens))
                    logging.info('deck type: {}'.format(self.deck['type']))
                    self.deck['type'] = command_tokens[1]
                    self.deck['composition'] = 'full_deck'
                    self.set_deck()
                    redis.set(from_id, command_tokens[1])
                    logging.info('{0} set deck as {1}'.format(sender, command_tokens[1]))

            elif command_tokens[0] in ('/draw', '/draw@sybilforkbot'):
                if len(self.deck['deck_object']) > 0:
                    card = self.deck['deck_object'].pop()
                    logging.info('{0} received {1}'.format(sender, card))
                    if 'majors' not in card.image:
                        caption = card.rank + ' of ' + card.kind
                    else:
                        caption = card.rank + ': ' + card.kind
                    self.sender.sendPhoto(open(card.image, 'rb'), caption=caption)
                else:
                    self.sender.sendMessage('The deck is out of cards!')
                self.sender.sendMessage('Your deck has {} cards left'.format(len(self.deck['deck_object'])))

            elif command_tokens[0] in ('/listtypes', '/listtypes@sybilforkbot'):
                decklist = ""
                for entry in self.deck_ref.keys():
                    decklist += "{}: {}\n".format(entry, self.deck_ref[entry][3])
                self.sender.sendMessage(decklist)
            
            elif command_tokens[0] in ('/help', '/help@sybilforkbot'):
                self.sender.sendMessage("All commands are prefixed by a forward slash (/), with no spaces between the" +
                                        " slash and your command. Dealt cards remain out of the deck until you issue a 'Majors', 'Minors', " +
                                        "'Full', 'Settype', or 'Shuffle' command.\n " +
                                        "These are the commands I currently understand:\n\n" +
                                        "Majors -- Set deck to deal only from the Major Arcana\n" +
                                        "Minors -- Set deck to deal only the pips\n" +
                                        "Full -- Set deck to deal both Majors and Minors\n" +
                                        "Listtypes -- List the types of decks available for use\n" +
                                        "Settype [type] -- Sets to one of the decks listed in Listtypes, eg: /settype " +
                                        "jodocamoin Note: This reshuffles the deck\n" +
                                        "Draw -- Draw a card\n" +
                                        "Help -- This text\n")

if __name__ == '__main__':
    token = sys.argv[1]
    setup_logger('sybil')
    logging.info('Starting bot with token {}'.format(token))
    redis = redis.StrictRedis(host='localhost', port=6379, db=0)
    sybil = telepot.DelegatorBot(token, [pave_event_space()(per_chat_id(), create_open, Sybil, timeout=600)])
    logging.info('Waiting for messages')
    MessageLoop(sybil).run_as_thread()
    while 1:
        time.sleep(1)
