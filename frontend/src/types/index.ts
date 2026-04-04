export interface Task {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  createdAt: string;
}

export interface Activity {
  id: string;
  type: 'log' | 'error' | 'success';
  message: string;
  timestamp: string;
}
