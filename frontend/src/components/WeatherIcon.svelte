<!-- Weather icon for a WMO code (Open-Meteo). SVG, not emoji: emoji render as tofu in the pixel font. -->
<script module lang="ts">
  export type WeatherCategory = 'sun' | 'partly' | 'cloud' | 'fog' | 'rain' | 'snow' | 'thunder';

  export function categoryOf(code: number): WeatherCategory {
    if (code === 0 || code === 1) return 'sun';
    if (code === 2) return 'partly';
    if (code === 3) return 'cloud';
    if (code === 45 || code === 48) return 'fog';
    if ((code >= 71 && code <= 77) || code === 85 || code === 86) return 'snow';
    if (code >= 95) return 'thunder';
    if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) return 'rain';
    return 'cloud';
  }

  /** i18n key of a short condition label. */
  export function conditionKey(code: number): string {
    if (code === 0) return 'weather.clear';
    if (code === 1) return 'weather.mostly_clear';
    if (code === 2) return 'weather.partly_cloudy';
    if (code === 45 || code === 48) return 'weather.fog';
    if (code >= 51 && code <= 57) return 'weather.drizzle';
    if (code >= 61 && code <= 67) return 'weather.rain';
    if (code >= 71 && code <= 77) return 'weather.snow';
    if (code >= 80 && code <= 82) return 'weather.showers';
    if (code === 85 || code === 86) return 'weather.snow_showers';
    if (code >= 95) return 'weather.storms';
    return 'weather.cloudy';
  }
</script>

<script lang="ts">
  let { code, size = 22 }: { code: number; size?: number } = $props();
  const cat = $derived(categoryOf(code));
  const cloud = 'M7 18a4 4 0 0 1 0-8 5 5 0 0 1 9.6-1.3A3.5 3.5 0 0 1 18 18H7z';
</script>

<svg class="wi wi-{cat}" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
  {#if cat === 'sun'}
    <circle class="wi-sun" cx="12" cy="12" r="5" />
    <g class="wi-sun-rays"><path d="M12 1v3M12 20v3M1 12h3M20 12h3M4 4l2 2M18 18l2 2M20 4l-2 2M6 18l-2 2" /></g>
  {:else}
    {#if cat === 'partly'}<circle class="wi-sun" cx="9" cy="8" r="3.5" />{/if}
    <path class="wi-cloud" d={cloud} />
    {#if cat === 'fog'}<g class="wi-fog"><path d="M4 21h16M6 23.5h12" /></g>{/if}
    {#if cat === 'rain'}<g class="wi-rain"><path d="M8 20l-1 2.5M13 20l-1 2.5M18 20l-1 2.5" /></g>{/if}
    {#if cat === 'snow'}
      <g class="wi-snow"><circle cx="8" cy="21.5" r="1" /><circle cx="13" cy="21.5" r="1" /><circle cx="18" cy="21.5" r="1" /></g>
    {/if}
    {#if cat === 'thunder'}<path class="wi-bolt" d="M12 19l-3 4h2.2L10 26l4-5h-2.3l1.3-2z" />{/if}
  {/if}
</svg>
