variable "aws_region" {
  description = "AWS region for the Terraform state bucket."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Prefix used for state infrastructure names."
  type        = string
  default     = "lionsforge"
}

variable "force_destroy" {
  description = "Allow destruction of a non-empty state bucket. Keep false outside disposable environments."
  type        = bool
  default     = false
}
