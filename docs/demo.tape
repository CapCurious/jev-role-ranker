# Record with: vhs docs/demo.tape   (run from the repository root; replays recorded data, no key)
Output docs/demo.gif

Set Shell "bash"
Set FontSize 14
Set Width 1100
Set Height 540
Set Padding 14
Set TypingSpeed 20ms
Set Framerate 12
Set PlaybackSpeed 1

Hide
Type "export PS1='$ ' && unset JEV_API_KEY TYPESAFE_API_KEY"
Enter
Type "clear"
Enter
Show

Type "python3 jev_role_ranker.py --demo rank examples/postings --limit 8"
Sleep 400ms
Enter
Sleep 4s

Type "python3 jev_role_ranker.py --demo rank examples/postings --limit 8 --sort fit"
Sleep 400ms
Enter
Sleep 5s
