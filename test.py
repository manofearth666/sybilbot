import tarotdeck
import json
import pprint
import cPickle as pickle

mock = tarotdeck.TarotDeck('crowleythoth')

def test():
	bin = pickle.dumps(mock)
	pprint.pprint(bin)

	obj = pickle.loads(bin)

	pprint.pprint(obj)