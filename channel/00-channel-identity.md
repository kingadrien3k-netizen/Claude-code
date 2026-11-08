# Channel Identity

## Name: **Hypothetica**
Tagline: *"One impossible question. Followed to the very end."*

Handle ideas: `@hypotheticatv`, `@hypothetica.stories`

## Format: voiceless
No narrator. Every story is told with **on-screen text** over animation and an ambient music score.
- Text sits in the bottom widescreen bar, one short line at a time, timed for comfortable reading (~15 characters per second, minimum 3 seconds).
- Music carries the emotion: soft pads + bell notes, and it **drops to silence right before the twist**.
- Works for viewers with sound off, and translates easily (swap the text for other languages).

## About text (paste into YouTube)
> Welcome to Hypothetica. Every episode asks one impossible question — and then refuses to stop asking. What happens on day one? Year one? What does real science say would actually break first?
>
> Silent cinematic stories, real research, and an ending you won't see coming.
>
> New episodes every week. Drop your own "what if" in the comments — the best ones get made.

## Visual style
- **Cinematic silhouettes.** Solid black figures and objects against glowing gradient skies (sunset, dawn, night, warm interiors). Widescreen black bars and light film grain.
- **One color per episode.** The impossible thing is always shown in a single accent color (episode 1 = amber `#FFB040`). One rare second color can mark a key plot object (episode 1 = the red umbrella).
- **Main character: Wren.** A silhouette with square glasses sticking out past the profile and a scarf that blows in the wind. Wren is the main character in every story (different life each time).
- **Science cards.** When real science shows up, a cream "REAL SCIENCE" index card slides in with a short fact.
- **Ending signature.** Every episode ends on black with one amber word.

## Structure
**Hook (question to the viewer) → Title card → Day One → Escalation → Real Science → The Cost → Twist (music cuts out) → Reveal → One-word ending**

Length: 3–5 minutes.

## Thumbnail formula
Big black silhouette of Wren against a bright sky, the episode's accent-color object glowing beside it, 3–4 words of text max.

## Upload schedule
1 episode per week + 2–3 Shorts cut from the hook and twist.

## How episodes are made
`channel/preview/render_episode.py` generates the whole episode (animation, text, and music) — see `channel/preview/README.md`.
