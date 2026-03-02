import { createContext, useContext, useState, useEffect, useRef } from "react";

/* ─── Hardcoded AI results ─────────────────────────────────────────── */
const RUBRIC_CRITERIA = [
  { criterion: "Correctness & Output",  desc: "Code produces correct results for all test cases",          max: 40 },
  { criterion: "Code Quality & Style",  desc: "Clean, readable code with proper naming conventions",       max: 20 },
  { criterion: "OOP Design",           desc: "Proper class hierarchy, encapsulation, and inheritance",     max: 20 },
  { criterion: "Documentation",        desc: "Meaningful comments, Javadoc, and inline explanations",     max: 10 },
  { criterion: "Exception Handling",   desc: "Try-catch blocks, custom exceptions, and edge-case safety", max: 10 },
];

export const AI_RESULTS = {
  1: {
    rubric: [
      { ...RUBRIC_CRITERIA[0], score: 38 },
      { ...RUBRIC_CRITERIA[1], score: 18 },
      { ...RUBRIC_CRITERIA[2], score: 19 },
      { ...RUBRIC_CRITERIA[3], score: 9  },
      { ...RUBRIC_CRITERIA[4], score: 9  },
    ],
    total: 93, max: 100, verdict: "Excellent",
    feedback:
      "This is an excellent implementation of the Banking System project. The student demonstrates " +
      "a strong grasp of object-oriented design principles, implementing a well-structured class " +
      "hierarchy with BankAccount, SavingsAccount, and TransactionHistory classes. Error handling " +
      "is thorough with custom exceptions for insufficient funds and invalid operations. The code " +
      "is clean, well-commented, and follows Java naming conventions throughout. Minor deduction " +
      "for not handling the edge case of concurrent transactions. Overall, this submission reflects " +
      "a deep understanding of the course material.",
    extractedCode:
`public class BankAccount {
    private final String accountId;
    private double balance;
    private List<Transaction> history;

    public BankAccount(String accountId, double initialBalance) {
        if (initialBalance < 0)
            throw new IllegalArgumentException(
                "Initial balance cannot be negative");
        this.accountId = accountId;
        this.balance   = initialBalance;
        this.history   = new ArrayList<>();
    }

    public synchronized void deposit(double amount) {
        if (amount <= 0)
            throw new IllegalArgumentException(
                "Deposit amount must be positive");
        balance += amount;
        history.add(new Transaction("DEPOSIT", amount));
    }

    public synchronized void withdraw(double amount)
            throws InsufficientFundsException {
        if (amount > balance)
            throw new InsufficientFundsException(amount, balance);
        balance -= amount;
        history.add(new Transaction("WITHDRAWAL", amount));
    }

    public double getBalance() { return balance; }
    public List<Transaction> getHistory() {
        return Collections.unmodifiableList(history);
    }
}`,
  },
  2: {
    rubric: [
      { ...RUBRIC_CRITERIA[0], score: 20 },
      { ...RUBRIC_CRITERIA[1], score: 8  },
      { ...RUBRIC_CRITERIA[2], score: 10 },
      { ...RUBRIC_CRITERIA[3], score: 3  },
      { ...RUBRIC_CRITERIA[4], score: 2  },
    ],
    total: 43, max: 100, verdict: "Needs Improvement",
    feedback:
      "This submission has significant issues that must be addressed before resubmission. " +
      "The code entirely lacks object-oriented design — all banking logic is placed inside a " +
      "single procedural main() method with no class design whatsoever. Variable names are " +
      "cryptic (x, y, temp), making the code extremely hard to follow. There is no exception " +
      "handling: the program crashes on invalid input, and negative deposit amounts are silently " +
      "accepted. The withdrawal logic contains a bug that can result in a negative balance " +
      "without any warning. Comments are sparse and add no value. This submission needs " +
      "major revision to meet the minimum course requirements for OOP design.",
    extractedCode:
`public class Main {
    public static void main(String[] args) {
        // bank program
        int x = 1000;   // balance???
        int y = 0;

        // deposit
        x = x + 500;
        System.out.println("balance: " + x);

        // withdraw
        x = x - 200;
        System.out.println("balance: " + x);

        // transfer
        int temp = x;
        x = x - 300;
        y = y + 300;
        System.out.println("done");
        // no error check anywhere
    }
}`,
  },
};

/* ─── localStorage helpers ───────────────────────────────────────────── */
const STORAGE_KEY = "jsg_submissions_v1";

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    // fileUrl is a blob: URL — only valid within the tab that created it,
    // so we clear it when loading from storage (image will show placeholder).
    return JSON.parse(raw).map((s) => ({ ...s, fileUrl: null }));
  } catch {
    return [];
  }
}

function saveToStorage(subs) {
  try {
    // Strip the blob URL before serialising — it can't survive across sessions.
    const serialisable = subs.map(({ fileUrl, ...rest }) => rest);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serialisable));
  } catch { /* quota errors etc. — silently ignore */ }
}

/* ─── Context ────────────────────────────────────────────────────────── */
const SubmissionsContext = createContext();

export function SubmissionsProvider({ children }) {
  // Initialise from localStorage so state survives page refreshes.
  const [submissions, setSubmissions] = useState(loadFromStorage);

  // In-memory map of id → blob URL (only valid in the current tab/session).
  const sessionUrls = useRef({});

  // Persist to localStorage whenever submissions change.
  useEffect(() => {
    saveToStorage(submissions);
  }, [submissions]);

  // Sync across browser tabs via the storage event.
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        try {
          const fresh = JSON.parse(e.newValue).map((s) => ({ ...s, fileUrl: null }));
          setSubmissions(fresh);
        } catch { /* ignore malformed data */ }
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Merge in-session blob URLs so the uploader's tab still shows the image.
  const submissionsWithUrls = submissions.map((s) => ({
    ...s,
    fileUrl: sessionUrls.current[s.id] ?? null,
  }));

  /* ── addSubmission ────────────────────────────────────────────────── */
  const addSubmission = ({ studentName, fileUrl, filename, caseType }) => {
    const id = Date.now();
    const now = new Date().toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });

    // Keep the blob URL in memory only (not in localStorage).
    if (fileUrl) sessionUrls.current[id] = fileUrl;

    const newSub = {
      id,
      studentName,
      studentInitials: studentName.slice(0, 2).toUpperCase(),
      assignment: "Final Project - Banking System",
      course: "CS201",
      courseFull: "Object Oriented Programming",
      filename,
      fileUrl: null,   // stored without URL; merged back via submissionsWithUrls
      caseType,
      submittedAt: now,
      status: "Processing",
      aiResult: null,
    };

    setSubmissions((prev) => [newSub, ...prev]);

    // Simulate AI grading (3 seconds).
    setTimeout(() => {
      setSubmissions((prev) =>
        prev.map((s) =>
          s.id === id
            ? { ...s, status: "AI Graded", aiResult: AI_RESULTS[caseType] }
            : s
        )
      );
    }, 3000);
  };

  /* ── publishGrade ─────────────────────────────────────────────────── */
  const publishGrade = (id) => {
    setSubmissions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: "Published" } : s))
    );
  };

  /* ── overrideGrade ────────────────────────────────────────────────── */
  const overrideGrade = (id, manualScore, manualFeedback) => {
    setSubmissions((prev) =>
      prev.map((s) =>
        s.id === id
          ? {
              ...s,
              status: "Published",
              aiResult: {
                ...s.aiResult,
                total: manualScore,
                feedback: manualFeedback,
                overridden: true,
              },
            }
          : s
      )
    );
  };

  /* ── clearAll (dev helper) ────────────────────────────────────────── */
  const clearAll = () => {
    sessionUrls.current = {};
    setSubmissions([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <SubmissionsContext.Provider
      value={{
        submissions: submissionsWithUrls,
        addSubmission,
        publishGrade,
        overrideGrade,
        clearAll,
      }}
    >
      {children}
    </SubmissionsContext.Provider>
  );
}

export function useSubmissions() {
  return useContext(SubmissionsContext);
}
