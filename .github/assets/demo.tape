# Regenerate with: vhs .github/assets/demo.tape
# (run from the repo root, with `uv sync` already done)
#
# NOTE: vhs 0.12.0 (the latest release at the time this was written) has a
# bug where it exits 0 and prints "Creating X.gif..." but writes no file —
# the recorder's context gets cancelled before Render() runs, so ffmpeg is
# never invoked. See https://github.com/charmbracelet/vhs/issues/787 (fix:
# https://github.com/charmbracelet/vhs/pull/789, unmerged as of this
# writing). If `vhs` silently produces nothing for you, either wait for
# that fix to land in a release, or build vhs from
# https://github.com/jgonmor16/vhs.git (branch fix/render-with-live-context)
# with `go build`.

Output .github/assets/demo.gif

Set Shell "bash"
Set FontSize 20
Set Width 1200
Set Height 680
Set Theme "Dracula"
Set TypingSpeed 45ms
Set Padding 20

Type "uv run python .github/assets/demo.py"
Enter
Sleep 3500ms

Type "cat demo_graph/graph.py"
Enter
Sleep 4500ms
