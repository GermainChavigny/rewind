<!--
  A/V sync test, started from the phone (Picture & sound): every second a
  white flash and a beep that the browser outputs at the same instant. If
  they do not land together on the TV, the phone shifts the sound live.
  Any remote key ends it; it stops by itself after a minute.
-->
<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { syncBeep } from '../lib/sound';
  import { tv } from '../lib/tv.svelte';

  let flash = $state(false);
  let count = $state(0);
  let timers: ReturnType<typeof setTimeout>[] = [];
  let loop: ReturnType<typeof setInterval> | undefined;

  function cycle() {
    if (Date.now() > tv.avTestUntil) {
      tv.avTestUntil = 0;
      return;
    }
    const delay = syncBeep() ?? 100;
    timers.push(
      setTimeout(() => {
        flash = true;
        count += 1;
      }, delay),
      setTimeout(() => (flash = false), delay + 90),
    );
    timers = timers.slice(-6);
  }

  onMount(() => {
    cycle();
    loop = setInterval(cycle, 1000);
  });
  onDestroy(() => {
    clearInterval(loop);
    timers.forEach(clearTimeout);
  });
</script>

<div class="test" class:flash>
  <div class="target"></div>
  <div class="caption">
    <strong>SYNCHRO SON / IMAGE</strong>
    <span>Le bip doit tomber pile sur le flash · {count}</span>
  </div>
</div>

<style>
  .test {
    position: absolute;
    inset: 0;
    z-index: 50;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 40px;
    background: #000;
    color: #fff;
  }
  .target {
    width: 220px;
    height: 220px;
    border: 6px solid #444;
    border-radius: 50%;
  }
  .flash .target {
    background: #fff;
    border-color: #fff;
    box-shadow: 0 0 80px #fff;
  }
  .caption {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    font-family: var(--crt-mono);
    font-size: 22px;
  }
  .caption span {
    font-size: 17px;
    color: #aaa;
  }
</style>
