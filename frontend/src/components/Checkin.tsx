import { useEffect, useState } from 'react';
import { getNextCheckin, answerCheckin } from '@/services/manager';

export default function Checkin() {
  const [question, setQuestion] = useState<{ qid: string; text: string } | null>(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    getNextCheckin()
      .then(setQuestion)
      .catch(err => setStatus(err.message));
  }, []);

  async function submit(value: number) {
    if (!question) return;
    const resp = await answerCheckin(question.qid, value);
    setStatus(`Recorded. BS=${resp.bs?.toFixed(2)} (next in ~${resp.next_interval_min} min)`);
  }

  return (
    <div>
      <p>{question?.text ?? 'Loading...'}</p>
      <button onClick={() => submit(1)}>1</button>
      <button onClick={() => submit(5)}>5</button>
      <p>{status}</p>
    </div>
  );
}
