output "eks_cluster_name" {
  value       = module.eks.cluster_name
  description = "EKS cluster name"
}

output "eks_cluster_endpoint" {
  value       = module.eks.cluster_endpoint
  description = "EKS API server endpoint"
}

output "redis_primary_endpoint" {
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  description = "Primary Redis endpoint for Feast online store"
}

output "s3_bucket_raw" {
  value       = aws_s3_bucket.raw.bucket
  description = "Raw data lake bucket name"
}

output "s3_bucket_processed" {
  value       = aws_s3_bucket.processed.bucket
  description = "Processed data lake bucket name"
}
