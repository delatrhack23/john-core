#!/usr/bin/env python3
"""
Simulateur pedagogique de minage de cryptomonnaie (Proof of Work).

But: comprendre CONCRETEMENT comment fonctionne le minage utilise par des
cryptomonnaies comme Bitcoin, sans se connecter a un vrai reseau ni a un
pool de minage. Ce script est 100% local, hors-ligne et ne produit aucune
cryptomonnaie reelle.

Principe de la preuve de travail (Proof of Work):
    1. On assemble les donnees d'un bloc (index, horodatage, donnees,
       hash du bloc precedent, nonce).
    2. On calcule le hash SHA-256 de ce bloc.
    3. Si le hash ne commence pas par un nombre suffisant de zeros
       (la "difficulte"), on incremente le nonce et on recommence.
    4. Le premier a trouver un hash valide "gagne" le droit d'ajouter
       le bloc a la chaine (et recoit une recompense dans un vrai reseau).

Plus la difficulte est elevee, plus il faut essayer de nonces avant de
trouver un hash valide, donc plus il faut de puissance de calcul.

Usage:
    python3 miner.py                  # difficulte par defaut (4)
    python3 miner.py --difficulty 5   # augmenter la difficulte
    python3 miner.py --blocks 3       # miner plusieurs blocs a la suite
"""

from __future__ import annotations

import argparse
import hashlib
import time
from dataclasses import dataclass, field


@dataclass
class Block:
    """Un bloc simplifie d'une blockchain pedagogique."""

    index: int
    timestamp: float
    data: str
    previous_hash: str
    nonce: int = 0
    hash: str = field(default="", init=False)

    def compute_hash(self) -> str:
        """Calcule le hash SHA-256 du contenu du bloc (avec le nonce actuel)."""
        block_content = (
            f"{self.index}{self.timestamp}{self.data}"
            f"{self.previous_hash}{self.nonce}"
        )
        return hashlib.sha256(block_content.encode("utf-8")).hexdigest()


def mine_block(index: int, data: str, previous_hash: str, difficulty: int) -> tuple[Block, float, int]:
    """
    "Mine" un bloc: cherche un nonce tel que le hash du bloc commence par
    `difficulty` zeros.

    Retourne le bloc mine, le temps ecoule en secondes, et le nombre
    d'essais (hashs calcules) necessaires.
    """
    target_prefix = "0" * difficulty
    block = Block(index=index, timestamp=time.time(), data=data, previous_hash=previous_hash)

    start = time.perf_counter()
    attempts = 0
    while True:
        block.hash = block.compute_hash()
        attempts += 1
        if block.hash.startswith(target_prefix):
            break
        block.nonce += 1
    elapsed = time.perf_counter() - start

    return block, elapsed, attempts


def print_block_summary(block: Block, elapsed: float, attempts: int) -> None:
    hashrate = attempts / elapsed if elapsed > 0 else float("inf")
    print(f"Bloc #{block.index} mine avec succes !")
    print(f"  Donnees          : {block.data!r}")
    print(f"  Hash precedent   : {block.previous_hash}")
    print(f"  Nonce trouve     : {block.nonce}")
    print(f"  Hash du bloc     : {block.hash}")
    print(f"  Essais (hashs)   : {attempts}")
    print(f"  Temps ecoule     : {elapsed:.3f} s")
    print(f"  Vitesse (H/s)    : {hashrate:,.0f} hashs/seconde")
    print()


def run_demo(num_blocks: int, difficulty: int) -> None:
    print("=== Simulateur pedagogique de minage (Proof of Work) ===")
    print(f"Difficulte choisie : {difficulty} (le hash doit commencer par {difficulty} zero(s))")
    print("Ceci est une simulation locale, aucune vraie cryptomonnaie n'est minee.\n")

    previous_hash = "0" * 64  # hash du bloc "genese"
    chain: list[Block] = []

    for i in range(1, num_blocks + 1):
        data = f"Transactions du bloc {i}"
        block, elapsed, attempts = mine_block(i, data, previous_hash, difficulty)
        print_block_summary(block, elapsed, attempts)
        chain.append(block)
        previous_hash = block.hash

    total_attempts = sum(1 for _ in chain)  # nombre de blocs, juste pour info
    print(f"Chaine finale: {len(chain)} bloc(s) mine(s) avec succes.")
    print("Astuce: augmentez --difficulty pour voir le nombre d'essais et le")
    print("temps de calcul augmenter de facon exponentielle (comme pour un")
    print("vrai reseau de minage).")
    _ = total_attempts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulateur pedagogique de minage de cryptomonnaie (Proof of Work).",
    )
    parser.add_argument(
        "--difficulty",
        type=int,
        default=4,
        help="Nombre de zeros requis au debut du hash (defaut: 4). "
        "Attention, au-dela de 6-7 le calcul peut devenir long sur un CPU classique.",
    )
    parser.add_argument(
        "--blocks",
        type=int,
        default=1,
        help="Nombre de blocs a miner a la suite (defaut: 1).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.difficulty < 0:
        raise SystemExit("La difficulte doit etre un entier positif ou nul.")
    if args.blocks < 1:
        raise SystemExit("Le nombre de blocs doit etre superieur ou egal a 1.")
    run_demo(num_blocks=args.blocks, difficulty=args.difficulty)


if __name__ == "__main__":
    main()
