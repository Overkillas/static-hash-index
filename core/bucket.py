"""
Módulo: core/bucket.py
=======================
Define as estruturas BucketEntry e Bucket para o índice hash.

O que é um bucket?
------------------
No índice hash, o arquivo de índice é dividido em NB "caixas" (buckets).
Cada chave (palavra) é mapeada por uma função hash para exatamente um bucket.
O bucket armazena entradas do tipo (chave → page_id), apontando para a página
onde a palavra está no arquivo de dados.

Capacidade e Overflow:
-----------------------
Cada bucket primário tem capacidade máxima de FR entradas (Fator de Recarga).
Quando um bucket está cheio e precisa receber mais uma entrada, ocorre:

1. COLISÃO: a inserção "colidiu" com um bucket cheio.
2. OVERFLOW: cria-se um novo bucket encadeado ao final da lista.

A estrutura resultante é uma lista ligada de buckets:

    Bucket[i] → [e1, e2, ..., e_FR]
        ↓ overflow
    Bucket[overflow1] → [e_FR+1, ..., e_2FR]
        ↓ overflow
    Bucket[overflow2] → [e_2FR+1, ...]
        ↓
       None

Busca com overflow:
--------------------
Para buscar uma chave, percorremos a cadeia de overflow do bucket primário
até encontrar a chave ou atingir None (não encontrada). Cada bucket lido
conta como 1 leitura de I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BucketEntry:
    """
    Representa uma entrada (ponteiro) no bucket do índice hash.

    Armazena a associação entre uma chave (palavra) e a página onde
    ela está fisicamente armazenada no arquivo de dados.

    Attributes:
        key:     A palavra indexada. Ex: "elephant".
        page_id: ID da página onde "elephant" está armazenada.
                 Para buscar o dado real, lemos Page[page_id].
    """

    key: str
    page_id: int


@dataclass
class Bucket:
    """
    Representa um bucket do índice hash com suporte a overflow chaining.

    Um bucket primário (ou de overflow) contém uma lista de BucketEntry.
    Quando a lista atinge FR entradas, o próximo bucket na cadeia é usado.

    Attributes:
        bucket_id: Identificador único do bucket. Buckets primários têm
                   IDs de 0 a NB-1. Buckets de overflow têm IDs >= NB.
        entries:   Lista de entradas armazenadas neste bucket.
                   Para buckets primários: máximo FR entradas.
        overflow:  Referência ao próximo bucket na cadeia de overflow.
                   None se este é o último bucket da cadeia.
    """

    bucket_id: int
    entries: list[BucketEntry] = field(default_factory=list)
    overflow: Bucket | None = None

    def is_full(self, fr: int) -> bool:
        """
        Verifica se este bucket atingiu sua capacidade máxima.

        Args:
            fr: Fator de Recarga — número máximo de entradas permitidas.

        Returns:
            True se len(entries) >= fr, False caso contrário.
        """
        return len(self.entries) >= fr

    def count_entries_in_chain(self) -> int:
        """
        Conta o total de entradas em toda a cadeia de overflow deste bucket.

        Percorre a lista ligada somando as entradas de cada bucket.
        Útil para debugging e estatísticas de distribuição.

        Returns:
            Total de entradas (chaves) nesta cadeia completa.
        """
        total = len(self.entries)
        node = self.overflow
        while node is not None:
            total += len(node.entries)
            node = node.overflow
        return total

    def count_overflow_buckets(self) -> int:
        """
        Conta quantos buckets de overflow existem encadeados após este bucket.

        Returns:
            Número de buckets de overflow (não conta o bucket atual).
        """
        count = 0
        node = self.overflow
        while node is not None:
            count += 1
            node = node.overflow
        return count

    def get_chain_summary(self) -> str:
        """
        Retorna uma descrição textual da cadeia de buckets para debug/UI.

        Exemplo de retorno:
            "Bucket#5[10 entries] → Bucket#4700[3 entries] → None"
        """
        parts: list[str] = []
        node: Bucket | None = self
        while node is not None:
            parts.append(f"Bucket#{node.bucket_id}[{len(node.entries)} entradas]")
            node = node.overflow
        return " → ".join(parts) + " → None"
