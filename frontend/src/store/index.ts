import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Task, Activity } from '../types';

interface AppState {
  tasks: Task[];
  activities: Activity[];
  language: 'en' | 'zh-CN';
  addTask: (task: Task) => void;
  addActivity: (activity: Activity) => void;
  setLanguage: (lang: 'en' | 'zh-CN') => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      tasks: [
        { id: '1', title: 'Implement frontend shell', status: 'in_progress', createdAt: new Date().toISOString() },
        { id: '2', title: 'Setup CI/CD pipeline', status: 'pending', createdAt: new Date().toISOString() }
      ],
      activities: [
        { id: '1', type: 'log', message: 'Initialized application', timestamp: new Date().toISOString() }
      ],
      language: 'en',
      addTask: (task) => set((state) => ({ tasks: [...state.tasks, task] })),
      addActivity: (activity) => set((state) => ({ activities: [...state.activities, activity] })),
      setLanguage: (language) => set({ language })
    }),
    {
      name: 'app-storage',
    }
  )
);
