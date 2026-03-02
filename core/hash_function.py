"""
Módulo: core/hash_function.py
==============================
Contém a função hash djb2 adaptada para strings.

O que é djb2?
-------------
djb2 é um algoritmo de hash criado por Dan Bernstein. Ele produz uma distribuição
uniforme para strings, o que significa que palavras diferentes tendem a cair em
buckets diferentes — reduzindo colisões no índice hash.

Como funciona:
--------------
1. Começa com um valor "mágico" h = 5381 (número primo, boa semente inicial).
2. Para cada caractere `c` da string, calcula:
       h = h * 33 + ord(c)
   A multiplicação por 33 é feita via shift de bits: (h << 5) + h
   isso é equivalente a h*32 + h = h*33, mas mais rápido em hardware.
3. Aplica módulo (% nb) para mapear o resultado ao intervalo [0, nb).
4. Usa abs() para garantir que o resultado nunca seja negativo (Python pode
   produzir inteiros negativos com operações de bit).

Propriedades garantidas:
------------------------
- Determinística: a mesma chave SEMPRE produz o mesmo bucket (RNF05).
- Distribuição uniforme para o vocabulário do inglês (palavras em words_alpha.txt).
- Tempo de execução O(|key|) — linear no tamanho da string.
"""


def hash_function(key: str, nb: int) -> int:
    """
    Calcula o índice do bucket para uma chave usando o algoritmo djb2.

    Args:
        key: Palavra (string) a ser indexada. Ex: "hello", "world".
        nb:  Número total de buckets no índice hash. O resultado estará
             sempre no intervalo [0, nb).

    Returns:
        Inteiro no intervalo [0, nb) indicando o bucket destino da chave.

    Exemplo:
        >>> hash_function("apple", 100)
        # algum número entre 0 e 99, sempre o mesmo para "apple" com nb=100
    """
    # Semente inicial — valor escolhido por Dan Bernstein por produzir
    # poucos colisões na prática com strings ASCII.
    h = 5381

    for c in key:
        # (h << 5) é h * 32; somando h temos h * 33.
        # Somar ord(c) mistura o novo caractere no hash acumulado.
        # Isso garante que a ordem dos caracteres importa:
        # "abc" e "cba" produzem hashes diferentes.
        h = ((h << 5) + h) + ord(c)

    # abs() evita índice negativo; % nb mapeia para [0, nb)
    return abs(h) % nb
