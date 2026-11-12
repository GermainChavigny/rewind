import { mount } from 'svelte';
import './app.css';
import App from './App.svelte';
import { tv } from './lib/tv.svelte';

mount(App, { target: document.getElementById('app')! });

// Debugging from the browser console / test scripts.
(window as unknown as { rewind: typeof tv }).rewind = tv;
