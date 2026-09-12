from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.domain.enums import RunStatus


class MatrixConfiguration(BaseModel):
    """Configuration for a single evaluation cell.
    
    Supports the full ARTEF evaluation matrix:
    Test Case × Model × Prompt Version × Provider × Dataset
    """
    # Model configuration
    model_id: str
    model_provider: str
    model_parameters: dict[str, Any] = Field(default_factory=dict)
    
    # Prompt configuration
    prompt_version_id: Optional[UUID] = None
    prompt_variables: dict[str, Any] = Field(default_factory=dict)
    
    # Dataset configuration
    dataset_id: Optional[UUID] = None
    dataset_version: Optional[int] = None
    dataset_split: Optional[str] = None  # train, val, test
    
    # Provider configuration
    provider_config: dict[str, Any] = Field(default_factory=dict)
    
    # Evaluation configuration
    judge_config: Optional[dict[str, Any]] = None
    redteam_config: Optional[dict[str, Any]] = None
    
    # Execution configuration
    max_retries: int = 3
    timeout_seconds: int = 300
    
    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationCell(BaseModel):
    """A single cell in the evaluation matrix: TestCase × Configuration."""
    id: UUID = Field(default_factory=uuid4)
    matrix_id: UUID
    test_case_id: UUID
    configuration: MatrixConfiguration
    run_id: Optional[UUID] = None
    status: RunStatus = RunStatus.QUEUED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EvaluationMatrix(BaseModel):
    """Evaluation matrix combining test cases with configurations."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    suite_id: UUID
    suite_version: int
    test_case_ids: list[UUID]
    configurations: list[MatrixConfiguration]
    cells: list[EvaluationCell] = Field(default_factory=list)
    status: RunStatus = RunStatus.QUEUED
    total_cells: int = 0
    completed_cells: int = 0
    failed_cells: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None

    def build_cells(self) -> list[EvaluationCell]:
        """Build all cells from test cases × configurations."""
        cells = []
        for test_case_id in self.test_case_ids:
            for config in self.configurations:
                cell = EvaluationCell(
                    matrix_id=self.id,
                    test_case_id=test_case_id,
                    configuration=config,
                )
                cells.append(cell)
        self.cells = cells
        self.total_cells = len(cells)
        return cells


class MatrixExecutionSummary(BaseModel):
    """Summary of matrix execution."""
    matrix_id: UUID
    total_cells: int
    completed_cells: int
    failed_cells: int
    queued_cells: int
    running_cells: int
    overall_status: RunStatus
    cells: list[EvaluationCell]