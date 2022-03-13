#! /usr/bin/python3
# import enchant
import re
import numpy as np
import multiprocessing as mp
from time import time, sleep
from typing import List, Dict, Set, Tuple
from functools import partial
from copy import copy


ALPHABET = set('abcdefghijklmnopqrstuvwxyz')
WORD_LEN = 5
WORD_COUNT = 4
TOTAL_GUESSES = 9

# TODO: Maybe done now? Account for double letter requirements. E.g.: You know the word must
#       contain at least 2 of the same letter (2 yellow matching letters in the same result),
#       but you don't know the position of either.

# TODO: add ability to use known filtered-out words as guesses if they have a better chance of
#       narrowing down the remaining words.

# TODO: Do something about duplicate letters. Just got "sassy" as a suggestion.

# TODO: When there are few options left for one word, pick a word that will narrow it down.
#       Had 2 problems in quordle that had "dread", "dream", "clock", and "chock" as options.
#       a single word guess that included an "m", "l", and "h" would have solved both at once.


class Problem:
	"""The current state of one of the words to be solved.

	number: `int`: Every letter that isn't in the word.
	unusedLetters `set`(`str`): Every letter that isn't in the word.
	letterCounts `dict`{`str` `int`}: A dict of the minimum number of times
		each letter appears in the word.
	positions `list`[`set`(`str`)]: For each position, there's a set of every
		letter that might be in that position. Set contains only one letter if
		the position has been solved.
	possibleWords `list`[`str`]: Every word that hasn't been ruled out.

	lastGuessResult `str`: Provided by the user; denotes the correctness of
		each letter in the last guess.
			0: letter is not in word
			1: letter exists in different position (yellow)
			2: letter is in correct position (green)
	"""
	number: int
	unusedLetters: Set[str]
	letterCounts: Dict[str, int]
	positions: List[Set[str]]
	possibleWords: List[str]
	positionSums: Dict[str, List[int]]
	guesses: List[str]
	lastGuessResult: str
	def __init__(self, number: int, words: List[str]):
		self.number = number
		self.unusedLetters = set()
		self.letterCounts = {l: 0 for l in ALPHABET}
		self.positions = [copy(ALPHABET) for _ in range(WORD_LEN)]
		self.possibleWords = copy(words)
		self.positionSums = dict()
		self.guesses = []
		self.lastGuessResult = '0' * WORD_LEN

	def getUserResponse(self) -> str:
		while True:
			response = input("Input the result for word #{}:  ".format(self.number))
			if set(response).difference("012"):
				print("\nPlease be sure to input the result as a {} digit ".format(WORD_LEN) +
				      "number consisting only of the following values:\n" +
				      "  0 - (Gray)   The letter isn't in the word.\n" +
				      "  1 - (Yellow) The letter is in a different position.\n" +
				      "  2 - (Green)  The letter is in the correct position.\n")
			elif len(response) != WORD_LEN:
				print("Please be sure that the number of digits matches the length of the word.")
			else:
				self.lastGuessResult = response
				return response

	def isValidWord(self, word: str) -> str:
		def containsLetters(word: str) -> bool:
			return all(word.count(letter) >= count for letter, count in self.letterCounts.items())
		def positionsMatch(word: str) -> bool:
			return all(word[i] in letters for i, letters in enumerate(self.positions))
		return (containsLetters(word) and positionsMatch(word) and word not in self.guesses)
			# self.possibleWords.remove(word)
		# print("\n" + str(word) + "\n" + str(containsLetters(word, self.letterCounts)) + "\n" + str(positionsMatch(word, self.positions)))
	def updateFromResult(self) -> bool:
		"""Rules out words that couldn't be possible based on the last guess result.
		`self.possibleWords` is then updated accordingly.

		Returns:
			bool: Whether or not this problem has been solved. Either because the
				user responded with "22222" or because there is only one possible
				word left.
		"""
		if self.lastGuessResult == "2" * WORD_LEN:
			self.possibleWords = [self.guesses[-1]]
			return True
		newLetterCounts = {}
		for i in re.finditer('2', self.lastGuessResult):
			self.positions[i.start()] = set([self.guesses[-1][i.start()]])
			if self.guesses[-1][i.start()] in newLetterCounts.keys():
				newLetterCounts[self.guesses[-1][i.start()]] += 1
			else:
				newLetterCounts[self.guesses[-1][i.start()]] = 1
		for i in re.finditer('1', self.lastGuessResult):
			self.positions[i.start()].difference_update(self.guesses[-1][i.start()])
			if self.guesses[-1][i.start()] in newLetterCounts.keys():
				newLetterCounts[self.guesses[-1][i.start()]] += 1
			else:
				newLetterCounts[self.guesses[-1][i.start()]] = 1
		for i in re.finditer('0', self.lastGuessResult):
			if not self.guesses[-1][i.start()] in newLetterCounts.keys():
				self.unusedLetters.add(self.guesses[-1][i.start()])


		for position in self.positions:
			position.difference_update(self.unusedLetters)

		for key, count in newLetterCounts.items():
			self.letterCounts[key] = max(count, self.letterCounts.get(key, 0))
		# Weed out words that aren't valid.
		start = time()
		self.possibleWords = [word for word in self.possibleWords if self.isValidWord(word)]
		print("removeIfInvalid done in " + str(time() - start))
		if len(self.possibleWords) == 1:
			return True
		return False

	def getMatchedLetters(self, letter: str, word: str) -> List[bool]:
		return [letter == l for i, l in enumerate(word) if self.positions[i] != l]
	def calcBasicScores(self) -> Dict[str, List[int]]:
		for letter in self.positionSums.keys():
			start = time()
			with mp.Pool(mp.cpu_count()) as pool:
				func = partial(self.getMatchedLetters, letter)
				letterMap = np.array(pool.map(func, self.possibleWords))
			print("getMatchedLetters done in " + str(time() - start))
			self.positionSums[letter] = np.sum(letterMap, axis=0)
			if sum(self.positionSums[letter]) == 0:
				self.positionSums.pop(letter)
		# totals = [[l, sum(sums)] for l, sums in positionSums.items()]
		# totals.sort(key=lambda x: x[1], reverse=True)
		# [["a", 24],              ["b", 24],                ...]

		# {"a": [10, 0, 0, 3, 11],  "b": [10, 0, 0, 3, 11],  ...}
		return self.positionSums

	def getWordScore(self, word: str) -> Tuple[str, int]:
		# TODO: maybe substitute sum for an algorithm that prefers all positions to have high
		# score instead of totals?
		default = [0] * WORD_LEN
		letterScores = []
		repeatLetterMod = 0
		for i, l in enumerate(word):
			# reapeadLetterMod is used to skew the algorithm away from choosing words that have
			# letters in the same position as previous guesses. So "stars" should have a
			# slightly lower score if "sorry" has already been guessed.
			repeatLetterMod += any(l == guess[i] for guess in self.guesses)
			dupeLetterMod = word.count(l)
			letterScores += [(self.positionSums.get(l, default)[i] /
			                  (word.count(l) * (1 + repeatLetterMod ** 2) * dupeLetterMod))]

		# TODO: Adjust multiplier in denominator until it stops suggesting so many words that
		#       have duplicate letters.
		# letterScores = [self.positionSums.get(l, default)[i] / (2 * word.count(l))
		#                 for i, l in enumerate(word)]
		return word, sum(letterScores)
	def calcWordScores(self) -> Tuple[Dict[str, List[int]],  Set[str]]:
		start = time()
		self.calcBasicScores()
		print("calcBasicScores done in " + str(time() - start))
		start = time()
		with mp.Pool(mp.cpu_count()) as pool:
			wordScores = pool.map(self.getWordScore, self.possibleWords)
		print("getWordScore done in " + str(time() - start))
		wordScores.sort(key=lambda x: x[1], reverse=True)
		wordScores = wordScores[:100]   # TODO: Adjust Trim value
		return set(pair[0] for pair in wordScores)


def getWordList() -> List[str]:
	def noSymbols(word: str) -> bool:
		return len(set(word).difference(ALPHABET)) == 0
	def isValidWord(word: str) -> bool:
		return (len(word) == WORD_LEN) and noSymbols(word) and (not word.isupper())
	with open("12dicts-6.0.2/Special/neol2016.txt", 'r') as wordListFile:
		neolList = [line[:-1].strip().split(", ") for line in wordListFile.readlines()]
	neolSet = set([word[:-1] if word.endswith("%") else word
	               for words in neolList  for word in words])
	with open("12dicts-6.0.2/American/2of12.txt", 'r') as wordListFile:
		words = set([word for line in wordListFile.readlines()
		             for word in line[:-1].strip().split(", ")])
	words = [word.lower() for word in list(words.union(neolSet)) if isValidWord(word.lower())]
	print(len(words))
	return words



if __name__ == "__main__":
	manager = mp.Manager()
	mp.set_start_method('spawn', True)
	words = getWordList()
	problems = [Problem(i + 1, words) for i in range(WORD_COUNT)]
	unspokenSolves = []
	# allWordScores = [problems[0].calcWordScores()]
	# allBasicScores = [problems[0].positionSums]
	guess = "coney"
	for guessIndex in range(TOTAL_GUESSES):
		print(guess)

		for problem in problems:
			problem.getUserResponse()

		solvedProblems = []
		# allBasicScores = []
		allWordScores = []
		for problem in problems:  # TODO: Can be parallelized.
			problem.guesses += [guess]
			if problem.updateFromResult():
				solvedProblems += [problem]
				if len(problem.possibleWords) != 1:
					print("UMMMMMM. ERROR???")
					print("problem " + str(problem.number) + " is marked as having its solution known, "\
						   "but here is the possibleWords list: " + str(problem.possibleWords))
					# TODO: THIS CAN BE REACHED BY CHANCE IF THE CORRECT WORD IS CHOSEN BEFORE THE LIST
					#       GETS NARROWED DOWN. FIXME
					# NOTE: ^ MAYBE FIXED NOW?
				if problem.guesses[-1] != problem.possibleWords[0]:
					unspokenSolves += [problem.possibleWords[0]]
				continue  # Word solved! wordState to be removed from list.

			allWordScores += [problem.calcWordScores()]
			# allBasicScores += [problem.positionSums]
			print(problem.possibleWords)

		if solvedProblems:
			[problems.remove(solvedProblem) for solvedProblem in solvedProblems]
			if not problems:
				break  # All problems solved!

		if len(unspokenSolves) != 0:
			guess = unspokenSolves[-1]
			print(unspokenSolves)
			print(guess)
			unspokenSolves.pop()
			print('in unspoken block')
			print(guess)
		else:
			topWords = set().union(*allWordScores)
			scores = []
			for word in topWords:
				score = sum(problem.getWordScore(word)[1] for problem in problems)
				scores += [[word, score]]
			scores.sort(key=lambda x: x[1], reverse=True)

			print('in else block')
			guess = scores[0][0]


	if problems:
		print("oh, I guess it failed. Sorry...")
	else:
		print("Yay!")
	# TODO: between "stars" and "stare", maybe prefer "stare"? Because it's more likely to
	# narrow down more letters.
