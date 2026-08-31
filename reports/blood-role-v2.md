# Naming a mechanism across four planes

`design_role` v1 read topology alone and could name five things. The evidence
said naming is cross-view — E1M1's rat trap and its curtain have identical
topological signatures — so v2 asks four planes independently and reports
**which one decided**.

```text
bloodmap/conditional.py     design_role, PLANES
reports/blood-role-v2.json
work/_role_v2_report.py
```

## The planes, in the order that breaks ties

| plane | evidence | why it ranks there |
| --- | --- | --- |
| **position** | the player starts inside it; it is half of a stack link | neither fact is about reachability, so nothing about reachability should overrule it |
| **dressing** | a **strong-binding** owner tile on the moving faces | the name is the owner's own label; weak and untested tiles never reach here |
| **contents** | a secret within reach of what it opens; dudes immediately beyond | "rats come out" is a stronger claim than "one sector fewer" |
| **topology** | one counterfactual: everything worked, against everything worked but this | the fallback, and the only plane that can say *nothing is claimed* |

`contested` lists planes that proposed something else. Two planes disagreeing
is not an error — it is two readings of one object.

## The owner's thirteen

```text
sector  owner name            v2                    decided by
30      narrative             narrative             position    OK
26      secret                secret                contents    OK
4       progression           recorded, not placed  topology    --
50      progression           recorded, not placed  topology    --
51      progression           recorded, not placed  topology    --
65      technical workaround  technical workaround  position    OK
90      technical workaround  technical workaround  position    OK
99      ambush                ambush                contents    OK
125     furnishing            ambush                contents    --
63      passage               secret                contents    --
70      secret entrance       secret                contents    --
86      fixture               fixture               topology    OK
139     fixture               fixture               topology    OK
```

**7 of 13**, against 5 for the topology-only version. Decided by: position 3,
contents 5, topology 5.

Features were **not** tuned to hit thirteen labels. Each miss is traceable:

- **s4, s50, s51** — unplaceable, and honestly so. Which state of a swept
  mechanism blocks is the parked polygon sweep; topology declines rather than
  guessing.
- **s125 (curtain → ambush)** — the most useful miss in the run. The contents
  plane sees dudes beyond and fires. The dressing plane *would* have named it
  from its tile, and is silent because **tile 146 has no owner binding**. A
  binding for 146 fixes this. That is a request to the owner, not a knob.
- **s63 (plain door → secret)** — a secret sits one hop beyond it. The
  contents plane cannot tell "leads to a secret" from "is the secret's door".
- **s70 (secret entrance → secret)** — the secret is one hop past its join
  rather than in it, so the entrance/reveal distinction is lost.

## E1M4, for scale

```text
26 gating mechanisms
  side passage 7   secret 6   ambush 6   fixture 4   required passage 2
  secret entrance 1
decided by: topology 13, contents 13
contested: 13 of 26
```

Half the mechanisms have two planes proposing different names. That is the
expected shape of a cross-view reading and the reason both are recorded.

## The dressing plane is silent on E1M1, by the rule

None of the thirteen wears a strong-binding owner tile on its moving faces.
s125 wears 146, s65 wears 1044, s4 and s50/51 wear 90 (`worn large bricks
with moss`, untested). Under the binding rule an untested tile is not
evidence, so the plane returns nothing rather than a guess.

This is the rule working, not failing. It also says exactly what would make
the plane useful: gradings for the tiles that dress mechanisms.

## Limitations

- **One attested map.** The owner has named thirteen mechanisms on E1M1.
  There is no held-out test, and **the cross-cut frequency is
  uncharacterised** — 7 of 13 is this map's number, not a rate.
- Three of the eight owner names (`furnishing`, `passage`, `progression` as
  distinct from required/side) are not recovered at all.
- The contents plane looks one hop beyond a join. A secret two rooms away is
  invisible to it, and one immediately beyond a neighbour looks like the
  mechanism's own.
- Campaign only.
