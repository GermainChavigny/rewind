import { mount } from 'svelte';
import './admin.css';
import Admin from './Admin.svelte';

mount(Admin, { target: document.getElementById('admin')! });
