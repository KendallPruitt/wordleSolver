import enchant
from copy import copy

enchDict = enchant.Dict("en_US")

alphabet = set(['abcdefghijklmnopqrstuvwxyz'])

useCounts = [[letter, sum(letter in word for word in words)] for letter in alphabet]
sortedUseCounts = sorted(useCounts, key=lambda x: x[1]).reverse()



wordLength = 5
wordCount = 1
totalGuesses = 7

def isValidWord(word):
	return (len(word) == wordLength + 1) and ("'" not in word) and (not word.isupper())


wordFile = open("wordList.txt", 'r').readLines()
words = [word[:-1].lower() for word in wordFile if isValidWord(word)]

# For each word that you need to solve (usually from 1-4), this list
# contains that word's current solve state (as a dict).
#
# notUsed - a set of every letter that isn't in the word.
# confirmedLetterCounts - a set of every letter that is definitely somewhere in the word
# positions - list of sets: for each position, there's a set of every letter that might
#             in that position. Set contains only one letter if the position has been solved.
# possibleWords - list of every word that hasn't been ruled out.
# TODO: account for double letter requirements. E.g.: You know the word must contain at least
#       2 of the same letter (2 yellow matching letters in the same result), but you don't
#       know the position of either.
wordStates = [{
	"notUsed": set(),
	"confirmedLetterCounts": {},
	"positions": [copy(alphabet)] * wordLength,
	"possibleWords": copy(words)
}] * wordCount



# TODO: REMOVE TEST DATA ---------------
currentWordIndex = 0
guess = "texas"
# --------------------------------------
wordState = wordStates[currentWordIndex]
positions = wordState["positions"]
for i in range(len(wordCount)):
	# 0 means letter is not in word
	# 1 means letter exists in different position (yellow)
	# 2 means letter is in correct position (green)
	guessResult = '00120' # TODO: REPLACE TEST DATA
	# dict with yellow and green letters as keys, and quantity as values
	confirmedLetterCounts = {}
	for j in range(wordLength):
		if guessResult[j] == '0':
			wordStates["notUsed"].add(guess[j])
		else:
			confirmedLetterCounts[guess[j]] = confirmedLetterCounts.get(guess[j], 0) + 1
			if guessResult[j] == '1':
				positions.remove([guess[j]])
			else:
				positions[j] = set([guess[j]])
	for key in confirmedLetterCounts.keys():
		wordState["confirmedLetterCounts"][key] = max(confirmedLetterCounts[key],
			wordState["confirmedLetterCounts"].get(key, 0))
	confirmedLetters = wordState["confirmedLetterCounts"].keys()
	# Weed out words that aren't valid.
	def containsLetters(word, letters):
		return all(word.count(l) >= n for l, n in letters)
	def positionsMatch(word, positions):
		return all(word[k] in position for k, position in enumerate(positions))
	for word in wordState["possibleWords"]:
		if not (containsLetters(word, confirmedLetters) and positionsMatch(word, positions)):
			wordState["possibleWords"].remove(word)


	for position in wordStates[currentWordIndex]["positions"]:
		position.difference_update(wordStates["notUsed"])


# TODO: between "stars" and "stare", maybe prefer "stare"? Because it's more likely to
# narrow down more letters.
