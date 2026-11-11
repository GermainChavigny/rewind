/**
 * Movie Advisor state. It is never reset by leaving the screen: you can go
 * and download one recommendation, then come back to the others.
 *
 * Option ids are English (that is what the AI receives); labels are translated.
 */

import { api, type Recommendation } from './api';
import { t } from './i18n';
import { library } from './library.svelte';

const THEMES = [
  'Western', 'Space', 'Sci-Fi', 'Fantasy', 'Medieval', 'War', 'Crime', 'Detective',
  'Horror', 'Creatures', 'Monsters', 'Zombies', 'Vampires', 'Robots', 'AI', 'Cyberpunk',
  'Post-apocalyptic', 'Time Travel', 'Superheroes', 'Martial Arts', 'Pirates', 'Samurai',
  'Espionage', 'Nature', 'Survival', 'Ocean', 'Mountains', 'Desert', 'Jungle', 'Arctic',
  'Documentary', 'Heist', 'Gangster', 'Film Noir', 'Thriller', 'Slasher', 'Disaster',
  'Musical', 'Sports', 'Boxing', 'Racing', 'Courtroom', 'Political', 'Biopic', 'Historical',
  'Coming-of-Age', 'Road Trip', 'Prison', 'Con Artists', 'Revenge', 'Kidnapping', 'Dystopia',
  'Steampunk', 'Mythology', 'Dragons', 'Vikings', 'Gladiators', 'Knights', 'Wizards',
  'Witches', 'Demons', 'Ghosts', 'Aliens', 'Kaiju', 'Mecha', 'Dinosaurs', 'Magic',
  'Assassins', 'Ninjas', 'Hackers', 'Treasure Hunt', 'Cars', 'Music', 'Dance', 'Family',
  'Christmas',
]; // prettier-ignore

export interface Criterion {
  key: string;
  options: string[]; // options[0] is always "Any"
}

export const CRITERIA: Criterion[] = [
  { key: 'mood', options: ['Any', 'Relax', 'Think', 'Laugh', 'Cry', 'Adrenaline', 'Mystery', 'Romance', 'Dark'] },
  { key: 'pace', options: ['Any', 'Fun', 'Serious', 'Epic', 'Weird', 'Cozy', 'Tense'] },
  { key: 'era', options: ['Any', '< 70s', '70s', '80s', '90s', '2000s', '2010+'] },
  { key: 'scale', options: ['Any', 'Blockbuster', 'Mid-budget', 'Indie'] },
  { key: 'rating', options: ['Any', 'Must watch', 'Great', 'Hidden gem'] },
  { key: 'length', options: ['Any', '< 90 min', '90–120 min', '> 120 min'] },
  { key: 'theme1', options: ['Any', ...THEMES] },
  { key: 'theme2', options: ['Any', ...THEMES] },
]; // prettier-ignore

/** Translated label of an option, or the option itself (e.g. "80s", "Western"). */
export function optionLabel(option: string): string {
  const key = `adv.opt.${option}`;
  const label = t(key);
  return label === key ? option : label;
}

const pick = <T>(list: T[]): T => list[Math.floor(Math.random() * list.length)];
const defaults = () => Object.fromEntries(CRITERIA.map((c) => [c.key, 'Any']));

class Advisor {
  view = $state<'criteria' | 'recs'>('criteria');
  values = $state<Record<string, string>>(defaults());
  keywords = $state('');
  kind = $state<'movie' | 'series'>('movie');
  /** null = a "forgotten" slot (the column keeps its place). */
  recs = $state<(Recommendation | null)[]>([]);
  picker = $state<string | null>(null);
  busy = $state(false);
  message = $state<string | null>(null);
  quote = $state('');

  open(): void {
    this.picker = null;
    this.quote = pick(QUOTES);
    if (!this.recs.some(Boolean)) this.view = 'criteria';
  }

  surprise(): void {
    this.values = Object.fromEntries(CRITERIA.map((c) => [c.key, pick(c.options)]));
  }

  async run(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.recs = [];
    this.view = 'recs';
    this.message = t('adv.consulting');
    try {
      const recs = await api.recommend(this.values, this.keywords, this.kind);
      this.recs = recs;
      this.message = recs.length ? null : t('adv.none');
    } catch (err) {
      this.message = t('adv.unavailable', { error: (err as Error).message });
    } finally {
      this.busy = false;
    }
  }

  forget(index: number): void {
    const rec = this.recs[index];
    if (!rec) return;
    this.recs[index] = null;
    void api.forget({ id: rec.id, title: rec.title, year: rec.year }).catch(() => {});
  }

  /** Already in the library (the AI may still suggest it under another title). */
  owned(rec: Recommendation): boolean {
    return library.items.some((m) => m.id === rec.id);
  }
}

// Michael Harper, the (fictional) 90s TV critic of the Advisor. One quote per
// opening, purely decorative. Short: the panel is ~21 characters wide.
export const QUOTES = [
  "I watch so you don't have to.",
  'Trust me. I have seen everything.',
  'Popcorn optional. Taste mandatory.',
  'I was right about that one. Again.',
  'Two thumbs. Both mine.',
  "They don't make them like this. Literally.",
  'I have opinions. Many opinions.',
  'The projector never lies.',
  'I gave it four stars. Under protest.',
  'Cinema is not dead. It is just napping.',
  'I have seen worse. Not much worse.',
  'This one holds up. Mostly.',
  'A masterpiece. Or close enough.',
  'I fell asleep. That is a review.',
  'Great films age. Bad films just get old.',
  'I do not review. I forgive.',
  'Subtitles build character.',
  'Black and white is a colour.',
  'The director knew. He simply did not care.',
  'Every frame a painting. Some abstract.',
  'I laughed. I cried. I checked my watch.',
  'Runtime is a promise, not a threat.',
  'The book was different. Not better.',
  'I have never walked out. Only left early.',
  'A sequel nobody asked for. I asked.',
  'Style over substance is still style.',
  'They filmed this on purpose.',
  'The score does the heavy lifting.',
  'Practical effects age like wine.',
  'I remember the ending. That is rare.',
  'Slow is not the same as boring.',
  'Loud is not the same as exciting.',
  'This aged like milk. Good milk.',
  'The critics were wrong. I was there.',
  'Underrated. By everyone but me.',
  'Overrated. Say it louder.',
  'A cult classic in waiting.',
  'The twist works. The first time.',
  'I own this on three formats.',
  'Widescreen or nothing.',
  'The trailer spoiled it. Watch anyway.',
  'Not for everyone. Perfect for someone.',
  'A flawed gem is still a gem.',
  'Ambitious. Which is half the battle.',
  'Nobody makes a clean 92 minutes anymore.',
  'The lighting is the whole plot.',
  'That performance deserved better.',
  'A cast this good is a small miracle.',
  'The edit saved it. Barely.',
  'Straight to video. Straight to my heart.',
  'A B-movie with an A-movie soul.',
  'Low budget. High ideas.',
  'Big budget. Small ideas.',
  'They spent it all on the first act.',
  'The third act forgives the second.',
  'I would watch this again. Reluctantly.',
  'Bring a blanket. And patience.',
  'Watch it late. It plays better.',
  'This one needs a rewatch. Or three.',
  'The sound design does the acting.',
  'A quiet film in a loud decade.',
  'Nobody understood it. Including me.',
  'Weird on purpose. My favourite kind.',
  'Genre is a suggestion.',
  'The rules were made to be broken. Gently.',
  'A love letter to nothing in particular.',
  'The camera moves. So should you.',
  'They shot it in 30 days. It shows. Nicely.',
  'Stunts real. Stakes realer.',
  'The villain steals it. As usual.',
  'A hero is only as good as the fall.',
  'The ending earns itself.',
  'No spoilers. Only warnings.',
  'I do not do star ratings. Here are four.',
  'Second viewing. Different film.',
  'It has a face only a critic could love.',
  'Bold. Which is to say strange.',
  'The pacing is a choice. A brave one.',
  'Three hours well spent. Roughly.',
  'Ninety minutes. Not one wasted.',
  "Under two hours. A gentleman's runtime.",
  'It knows exactly what it is.',
  'A crowd-pleaser with a mean streak.',
  'Funny until it is not. That is the trick.',
  'Sad in the good way.',
  'Scary in the cheap way. Still works.',
  'I jumped. Do not tell anyone.',
  'The monster is better unseen.',
  'The dog lives. You are welcome.',
  'Nobody says the title. Refreshing.',
  'The opening shot sells the whole thing.',
  'It peaks early. Then peaks again.',
  'Miscast. Magnificently.',
  'A director at the top of their game.',
  'A director figuring it out. On camera.',
  'The remake is fine. This is better.',
  'The original had less money. And more nerve.',
  'A franchise before that was a word.',
  'They ran out of film. Not ideas.',
  'One take. One legend.',
  'Made for nobody. Adored by many.',
  'Ahead of its time. Behind on plot.',
  'A perfect film. Do not @ me.',
  'Good taste is just my taste.',
  'Disagree. You will be wrong.',
  'Watch it. Then argue with me.',
];

export const advisor = new Advisor();
