export async function getNextCheckin() {
    const res = await fetch('/api/manager/checkin/next');
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json();
  }
  
  export async function answerCheckin(qid: string, value: number) {
    const res = await fetch('/api/manager/checkin/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ qid, value }),
    });
    if (!res.ok) throw new Error('Failed to submit answer');
    return res.json();
  }
  
  export async function advisorSupport(user: string, message: string) {
    const res = await fetch('/api/manager/support', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user, message }),
    });
    if (!res.ok) throw new Error('Support failed');
    return res.json();
  }
  
  export async function therapistTurn(user: string, message: string) {
    const res = await fetch('/api/manager/therapist/turn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user, message }),
    });
    if (!res.ok) throw new Error('Therapist turn failed');
    return res.json();
  }
  