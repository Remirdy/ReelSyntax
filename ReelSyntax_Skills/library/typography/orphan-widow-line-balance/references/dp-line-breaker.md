# Dynamic-Programming Balanced Line Breaker Algorithm

Given words `w[0..n-1]` with measured pixel widths `px[i]`, space width `sp`, and box limit `W`:
1. Bind inseparable `number + unit` pairs first.
2. Find minimum feasible line count `K`.
3. Over all splits into `K` lines with `line_w(l) <= W`, minimize:
   `cost = sum_l (target_w - line_w(l))^2 + sum_breaks penalty(last_word_of_line)`
   where `target_w = total_px / K`, `penalty = +400^2` if `last_word` is an article/preposition/conjunction, `penalty = -120^2` if `last_word` ends with `,` `;` `:`, and `+600^2` if `K >= 2` and `len(words_on_last_line) == 1` with `line_w(K-1) < 0.38 * max_l(line_w(l))`.
