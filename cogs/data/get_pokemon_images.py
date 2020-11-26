import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString

with open('pokemon_list.txt', 'r') as f:
    pokemons = f.read().split('\n')


with open("whosthatpokemon.yaml", 'w') as f:
    for pokemon in pokemons:
        print(pokemon)
        num, mon = pokemon.split(':')
        print("\"Who's That Pokemon? https://assets.pokemon.com/assets/cms2/img/pokedex/full/{}.png\":".format(num), file=f)
        print("- " + mon, file=f)