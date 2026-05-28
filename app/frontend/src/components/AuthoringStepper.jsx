import React from 'react';

const STEPS = [
  { id: 1, label: 'Describe', icon: '✎' },
  { id: 2, label: 'Understand', icon: '◉' },
  { id: 3, label: 'Clarify', icon: '?' },
  { id: 4, label: 'Preview', icon: '◫' },
  { id: 5, label: 'Validate', icon: '✓' },
  { id: 6, label: 'Lock', icon: '⊞' },
];

export default function AuthoringStepper({ currentStep }) {
  return (
    <div className="authoring-stepper">
      {STEPS.map((step, index) => {
        const isCompleted = currentStep > step.id;
        const isActive = currentStep === step.id;

        return (
          <React.Fragment key={step.id}>
            <div className={`authoring-step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}>
              <div className="authoring-step-node">
                {isCompleted ? '✓' : step.icon}
              </div>
              <span className="authoring-step-label">{step.label}</span>
            </div>
            {index < STEPS.length - 1 && (
              <div className={`authoring-step-connector ${isCompleted ? 'completed' : ''}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
