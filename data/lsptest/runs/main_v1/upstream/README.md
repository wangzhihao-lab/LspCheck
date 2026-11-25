# Upstream reports of the candidate bugs

`feedback.csv`: one row per candidate bug, with its tracker issue (filed after the campaign, 2026-09-28) and the
maintainers' response as of the date in `as_of`, classified by the author from the issue thread (classes revised on
2026-09-30, when `acknowledged` was split into `fix-planned` and `confirmed` and `closed-cause-confirmed` became `cause-confirmed`;
`investigating` added on 2026-10-02, `info-requested` added and `disputed` widened on 2026-10-07):

- fix-planned: a maintainer scheduled a fix (assigned the issue to a release with a proposed fix) or has a fix under review;
- confirmed: a maintainer labelled the issue as a bug or said it is one, without a planned fix;
- investigating: a maintainer took the issue (assigned it or labelled it for investigation) without a verdict yet;
- info-requested: a maintainer asked for more information (for example a reproduction in a common editor) without a verdict;
- fixed: a maintainer closed it as completed with a fix;
- cause-confirmed: a maintainer reproduced it and identified the faulty component, without a fix (the issue may be open or closed);
- disputed: a maintainer considers the behavior expected or a client error; the note gives the maintainer's reason and, if we replied, ours;
- no-reply: no reply from a maintainer yet (automatic bot comments do not count);
- not-reported: not filed, with the reason in `note`.

The replies are additional information for the paper; no verdict or evidence rests on them. The issue threads are public
(the `url` column); this file is updated by hand from them.
