#!/usr/bin/env python3
from pathlib import Path
import sys

def die(msg):
    raise SystemExit('R35.9 ABORT: ' + msg)

def rd(p):
    return p.read_text(encoding='utf-8-sig')

def wr(p,s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8', newline='\n')

def rep(s,a,b,label):
    if a not in s:
        die('ancre absente: ' + label)
    return s.replace(a,b,1)

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
for rel in [
    'src/Controller/SongLabController.php',
    'src/Service/ChordTimelineResultService.php',
    'templates/song/chordslab.html.twig',
    'public/assets/js/chordslab.js',
]:
    if not (root/rel).is_file():
        die('fichier absent: ' + rel)

# Fresh reanalysis must remove managed old timeline entities explicitly.
p = root/'src/Service/ChordTimelineResultService.php'
s = rd(p)
old = "        // R35.8a: fresh harmonic analysis is authoritative; old manual overrides are discarded.\n        $this->timeline->deleteMusicalAnalysisForSong($song);\n"
new = """        // R35.9: fresh harmonic analysis is authoritative.\n        // Explicit ORM removal avoids stale managed overrides surviving a reanalysis.\n        foreach ($this->timeline->findBeatEvents($song) as $existingBeat) {\n            $this->em->remove($existingBeat);\n        }\n        foreach ($this->timeline->findChordEvents($song) as $existingChord) {\n            $this->em->remove($existingChord);\n        }\n        $this->em->flush();\n"""
if old in s:
    s = s.replace(old,new,1)
elif '$this->em->remove($existingChord)' not in s:
    die('ancre purge R35.8a introuvable')
wr(p,s)

# Backend endpoint to edit ANY beat, including analysed '.' beats.
p = root/'src/Controller/SongLabController.php'
s = rd(p)
anchor = "    #[Route('/chords/event/{eventId}', name: 'app_song_chordslab_event', requirements: ['eventId' => '\\\\d+'], methods: ['POST'])]\n"
if 'app_song_chordslab_beat_override' not in s:
    method = r'''    #[Route('/chords/beat/{beatId}', name: 'app_song_chordslab_beat_override', requirements: ['beatId' => '\d+'], methods: ['POST'])]
    public function saveChordAtBeat(
        Song $song,
        int $beatId,
        Request $request,
        SongTimelineEventRepository $timeline,
        EntityManagerInterface $em,
    ): JsonResponse {
        $this->requireEditor($song);
        $payload = $request->toArray();

        if (!$this->isCsrfTokenValid(
            'song_chordslab_edit_'.$song->getId(),
            (string) ($payload['_token'] ?? ''),
        )) {
            return $this->json(['error' => 'invalid_csrf'], Response::HTTP_FORBIDDEN);
        }

        $profile = trim((string) ($payload['profile'] ?? $song->getChordAnalysisLevel()));
        if (!in_array($profile, ['beginner', 'intermediate', 'expert'], true)) {
            return $this->json(['error' => 'invalid_profile'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $beat = $timeline->find($beatId);
        if (!$beat instanceof SongTimelineEvent
            || $beat->getSong()->getId() !== $song->getId()
            || $beat->getEventType() !== SongTimelineEvent::TYPE_BEAT) {
            return $this->json(['error' => 'beat_not_found'], Response::HTTP_NOT_FOUND);
        }

        $chord = trim((string) ($payload['chord'] ?? ''));
        $chord = preg_replace('/^\\[([^\\]]+)\\]$/', '$1', $chord) ?? $chord;
        $chord = preg_replace('/^([A-G](?:#|b)?)maj$/', '$1', $chord) ?? $chord;

        if ($chord === '-') {
            return $this->json(['error' => 'continuation_is_display_only'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }
        if ($chord !== '.'
            && ($chord === '' || mb_strlen($chord) > 32
                || !preg_match('/^[A-G](?:#|b)?[A-Za-z0-9()+#b°øΔ\\/-]*$/u', $chord))) {
            return $this->json(['error' => 'invalid_chord'], Response::HTTP_UNPROCESSABLE_ENTITY);
        }

        $event = null;
        foreach ($timeline->findChordEventsForProfile($song, $profile) as $candidate) {
            if ($candidate->getStartMs() === $beat->getStartMs()) {
                $event = $candidate;
                break;
            }
        }

        if (!$event instanceof SongTimelineEvent) {
            $event = (new SongTimelineEvent($song, SongTimelineEvent::TYPE_CHORD, $beat->getStartMs()))
                ->setPosition($beat->getMeasureIndex(), $beat->getBeatIndex(), $beat->getSubdivisionIndex())
                ->setOriginalValue('.')
                ->setPayload([
                    'confidence' => 0.0,
                    'profile' => $profile,
                    'analysis_level' => $profile,
                    'analysis_version' => 'manual-beat-r35.9',
                ]);
            $em->persist($event);
        }

        if ($chord === '.') {
            $event->resetOverride();
        } else {
            $event->setOverrideValue($chord);
        }
        $em->flush();

        return $this->json([
            'ok' => true,
            'id' => $event->getId(),
            'start_ms' => $event->getStartMs(),
            'measure_index' => $event->getMeasureIndex(),
            'beat_index' => $event->getBeatIndex(),
            'original' => $event->getOriginalValue(),
            'override' => $event->getOverrideValue(),
            'effective' => $event->getEffectiveValue(),
        ]);
    }

'''
    if anchor not in s:
        # tolerate one-backslash source representation
        anchor = "    #[Route('/chords/event/{eventId}', name: 'app_song_chordslab_event', requirements: ['eventId' => '\\d+'], methods: ['POST'])]\n"
    s = rep(s,anchor,method+anchor,'beat override endpoint')
wr(p,s)

# Twig exposes beat-edit URL + cache bust.
p = root/'templates/song/chordslab.html.twig'
s = rd(p)
if 'data-beat-edit-url-template' not in s:
    anchor = "         data-edit-url-template=\"{{ path('app_song_chordslab_event', {'_locale': app.request.locale, id: song.id, eventId: 999999})|replace({'999999':'__EVENT__'}) }}\"\n"
    insert = anchor + "         data-beat-edit-url-template=\"{{ path('app_song_chordslab_beat_override', {'_locale': app.request.locale, id: song.id, beatId: 999999})|replace({'999999':'__BEAT__'}) }}\"\n"
    s = rep(s,anchor,insert,'beat edit URL')
s = s.replace('/assets/js/chordslab.js?v=20260928r35_8a','/assets/js/chordslab.js?v=20260928r35_9')
s = s.replace('/assets/js/chordslab.js?v=20260927r34_6','/assets/js/chordslab.js?v=20260928r35_9')
wr(p,s)

# JS: all beat cells editable.
p = root/'public/assets/js/chordslab.js'
s = rd(p)
old = "  measure.slots.push({seq,beatIndex,startMs:beat.start_ms,text,eventId:active?.id||null,editable:text!=='-'&&text!=='.'&&!!active?.id});\n"
new = """  measure.slots.push({
   seq,
   beatIndex,
   startMs:beat.start_ms,
   text,
   beatId:beat.id||null,
   eventId:exact?.id||null,
   activeEventId:active?.id||null,
   editable:!!beat.id
  });
"""
s = rep(s,old,new,'projection editable beat')

old = "   if(slot.eventId)b.dataset.eventId=String(slot.eventId);\n   b.innerHTML=formatChordHtml(slot.text); b.setAttribute('aria-label', slot.text);\n"
new = """   if(slot.eventId)b.dataset.eventId=String(slot.eventId);
   if(slot.beatId)b.dataset.beatId=String(slot.beatId);
   if(slot.activeEventId)b.dataset.activeEventId=String(slot.activeEventId);
   b.innerHTML=formatChordHtml(slot.text); b.setAttribute('aria-label', slot.text);
"""
s = rep(s,old,new,'render beat id')

start = s.find('async function editEvent(eventId,button){')
end = s.find('\nasync function persistProfile', start)
if start < 0 or end < 0:
    die('editEvent introuvable')
generic = r'''async function editSlot(button){
 const beatId=button.dataset.beatId;
 const activeEventId=button.dataset.activeEventId||'';
 if(!beatId)return;
 const active=activeEventId?events.find(e=>String(e.id)===String(activeEventId)):null;
 const input=document.createElement('input');
 input.className='chord-inline-input';
 const shown=button.getAttribute('aria-label')||'.';
 input.value=shown==='-' ? displayChord(active?.effective||active?.original||'') : shown;
 input.maxLength=32;
 button.replaceWith(input);input.focus();input.select();
 let finished=false;
 const restore=()=>{if(finished)return;finished=true;render()};
 const save=async()=>{
  if(finished)return;
  let chord=normaliseLabel(input.value.trim());
  if(!chord)chord='.';
  if(chord==='-'){restore();return}
  const url=(root.dataset.beatEditUrlTemplate||'').replace('__BEAT__',String(beatId));
  if(!url){input.classList.add('is-error');return}
  const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({_token:root.dataset.editToken,chord,profile:currentProfile})});
  if(!response.ok){input.classList.add('is-error');return}
  finished=true;
  window.location.reload();
 };
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();save()}if(e.key==='Escape'){e.preventDefault();restore()}});
 input.addEventListener('blur',save,{once:true});
}
'''
s = s[:start] + generic + s[end:]
old = "measuresEl.addEventListener('click',e=>{const b=e.target.closest('.chord-slot.editable[data-event-id]');if(b)editEvent(b.dataset.eventId,b)});\n"
new = """measuresEl.addEventListener('click',e=>{
 const b=e.target.closest('.chord-slot.editable[data-beat-id]');
 if(b)editSlot(b);
});
"""
s = rep(s,old,new,'click any beat')
wr(p,s)

print('R35_9_APPLIED_OK')
