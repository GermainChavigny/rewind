import { mount } from 'svelte';
import './app.css';
import App from './App.svelte';
import { tv } from './lib/tv.svelte';

mount(App, { target: document.getElementById('app')! });

// Debugging from the browser console / test scripts (like v1's window.tvApp).
(window as unknown as { rewind: typeof tv }).rewind = tv;
