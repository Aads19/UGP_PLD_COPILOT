type SuggestedQuestionsProps = {
  questions: string[];
  onSelect: (question: string) => void;
};

export function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="example-grid">
      {questions.map((question) => (
        <button key={question} onClick={() => onSelect(question)} type="button">
          {question}
        </button>
      ))}
    </div>
  );
}
