// src/hooks/useToast.js
import { useState, useCallback } from "react";

let _id = 0;
export function useToast() {
  const [toasts, setToasts] = useState([]);

  const add = useCallback((message, type = "info") => {
    const id = ++_id;
    setToasts(t => [...t, { id, message, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
  }, []);

  const remove = useCallback(id => setToasts(t => t.filter(x => x.id !== id)), []);

  const success = useCallback(m => add(m, "success"), [add]);
  const error   = useCallback(m => add(m, "error"),   [add]);
  const info    = useCallback(m => add(m, "info"),    [add]);

  return { toasts, remove, success, error, info };
}
