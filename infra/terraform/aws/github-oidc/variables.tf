variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "repository" {
  description = "GitHub repository in owner/name format."
  type        = string
  default     = "brandonpapasan-coder/LionsForge-ai"
}

variable "state_bucket_arn" {
  description = "ARN of the Terraform state bucket."
  type        = string
}
