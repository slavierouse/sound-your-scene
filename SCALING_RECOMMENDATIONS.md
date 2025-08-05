# Auto Scaling Recommendations

## Architecture Change
- **Before**: 1 large instance with 3 workers
- **After**: Multiple smaller instances with 1 worker each
- **Benefit**: Perfect session affinity + better fault tolerance

## AWS Auto Scaling Configuration

### Target Group Settings
```json
{
  "target_type": "instance",
  "health_check_path": "/health",
  "health_check_interval": 30,
  "healthy_threshold": 2,
  "unhealthy_threshold": 3,
  "stickiness": {
    "enabled": true,
    "duration_seconds": 3600,
    "type": "lb_cookie"
  }
}
```

### Auto Scaling Group
```json
{
  "min_size": 2,
  "max_size": 6,
  "desired_capacity": 2,
  "default_cooldown": 300,
  "health_check_type": "ELB",
  "health_check_grace_period": 300
}
```

### Scaling Policies

#### Scale Out (Up) Policies

**Policy 1: CPU-Based Scaling**
```json
{
  "policy_name": "ScaleOutCPU",
  "policy_type": "StepScaling",
  "adjustment_type": "ChangeInCapacity",
  "metric_aggregation_type": "Average",
  "step_adjustments": [
    {
      "metric_interval_lower_bound": 0,
      "metric_interval_upper_bound": 10,
      "scaling_adjustment": 1
    },
    {
      "metric_interval_lower_bound": 10,
      "scaling_adjustment": 2
    }
  ],
  "alarm_specification": {
    "alarm_name": "HighCPUUtilization",
    "metric_name": "CPUUtilization",
    "namespace": "AWS/EC2",
    "statistic": "Average",
    "unit": "Percent",
    "period": 300,
    "evaluation_periods": 2,
    "threshold": 70.0,
    "comparison_operator": "GreaterThanThreshold",
    "breach_duration": 600
  },
  "cooldown": 300
}
```

**Policy 2: Request Count Scaling**
```json
{
  "policy_name": "ScaleOutRequests", 
  "policy_type": "StepScaling",
  "adjustment_type": "ChangeInCapacity",
  "metric_aggregation_type": "Average",
  "step_adjustments": [
    {
      "metric_interval_lower_bound": 0,
      "metric_interval_upper_bound": 20,
      "scaling_adjustment": 1
    },
    {
      "metric_interval_lower_bound": 20,
      "scaling_adjustment": 2
    }
  ],
  "alarm_specification": {
    "alarm_name": "HighRequestCount",
    "metric_name": "RequestCountPerTarget", 
    "namespace": "AWS/ApplicationELB",
    "statistic": "Sum",
    "unit": "Count",
    "period": 300,
    "evaluation_periods": 2,
    "threshold": 100.0,
    "comparison_operator": "GreaterThanThreshold",
    "breach_duration": 600
  },
  "cooldown": 180
}
```

#### Scale In (Down) Policies

**Policy 3: CPU-Based Scale In**
```json
{
  "policy_name": "ScaleInCPU",
  "policy_type": "StepScaling", 
  "adjustment_type": "ChangeInCapacity",
  "metric_aggregation_type": "Average",
  "step_adjustments": [
    {
      "metric_interval_upper_bound": 0,
      "scaling_adjustment": -1
    }
  ],
  "alarm_specification": {
    "alarm_name": "LowCPUUtilization",
    "metric_name": "CPUUtilization",
    "namespace": "AWS/EC2", 
    "statistic": "Average",
    "unit": "Percent",
    "period": 300,
    "evaluation_periods": 3,
    "threshold": 25.0,
    "comparison_operator": "LessThanThreshold",
    "breach_duration": 900
  },
  "cooldown": 600
}
```

**Policy 4: Request Count Scale In**
```json
{
  "policy_name": "ScaleInRequests",
  "policy_type": "StepScaling",
  "adjustment_type": "ChangeInCapacity", 
  "metric_aggregation_type": "Average",
  "step_adjustments": [
    {
      "metric_interval_upper_bound": 0,
      "scaling_adjustment": -1
    }
  ],
  "alarm_specification": {
    "alarm_name": "LowRequestCount",
    "metric_name": "RequestCountPerTarget",
    "namespace": "AWS/ApplicationELB",
    "statistic": "Sum", 
    "unit": "Count",
    "period": 300,
    "evaluation_periods": 4,
    "threshold": 20.0,
    "comparison_operator": "LessThanThreshold", 
    "breach_duration": 1200
  },
  "cooldown": 900
}
```

#### Custom CloudWatch Metrics (Advanced)

**Active Jobs Metric**
```json
{
  "policy_name": "ScaleOutActiveJobs",
  "policy_type": "StepScaling",
  "adjustment_type": "ChangeInCapacity",
  "metric_aggregation_type": "Average", 
  "step_adjustments": [
    {
      "metric_interval_lower_bound": 0,
      "scaling_adjustment": 1
    }
  ],
  "alarm_specification": {
    "alarm_name": "HighActiveJobs",
    "metric_name": "ActiveSearchJobs",
    "namespace": "SoundByMood/Application",
    "statistic": "Average",
    "unit": "Count", 
    "period": 180,
    "evaluation_periods": 2,
    "threshold": 8.0,
    "comparison_operator": "GreaterThanThreshold",
    "breach_duration": 360
  },
  "cooldown": 240
}
```

**Memory Usage Metric**
```json
{
  "policy_name": "ScaleOutMemory",
  "policy_type": "StepScaling", 
  "adjustment_type": "ChangeInCapacity",
  "metric_aggregation_type": "Average",
  "step_adjustments": [
    {
      "metric_interval_lower_bound": 0,
      "scaling_adjustment": 1
    }
  ],
  "alarm_specification": {
    "alarm_name": "HighMemoryUsage", 
    "metric_name": "MemoryUtilization",
    "namespace": "SoundByMood/Application",
    "statistic": "Average",
    "unit": "Percent",
    "period": 300,
    "evaluation_periods": 2, 
    "threshold": 80.0,
    "comparison_operator": "GreaterThanThreshold",
    "breach_duration": 600
  },
  "cooldown": 300
}
```

## Recommended Instance Sizes

### Current Setup → New Setup
- **From**: 1x t3.medium (2 vCPU, 4GB) with 3 workers
- **To**: 2-3x t3.small (2 vCPU, 2GB) with 1 worker each

### Scaling Thresholds
- **Minimum**: 2 instances (fault tolerance)
- **Normal**: 2-3 instances (handles typical load)
- **Peak**: 4-6 instances (search traffic spikes)

### Cost Optimization
- **t3.small spot instances** for cost savings (search jobs are fault-tolerant)
- **Mixed instance types**: t3.small + t3.medium for flexibility
- **Scale-in protection** during active searches (optional)

## Monitoring Recommendations

### Key Metrics to Watch
1. **Request latency** (target: <2s average)
2. **Error rate** (target: <1%)
3. **Active jobs per instance** (target: <15)
4. **Database connections** (watch connection pool)
5. **Memory usage** (target: <80%)

### Alerts
- Scale up: Average CPU >70% for 5 minutes
- Scale up: Active jobs >10 per instance
- Scale down: Average CPU <30% for 10 minutes
- Scale down: Active jobs <3 per instance

## Deployment Strategy
1. ✅ Deploy Procfile change (1 worker per instance)
2. ✅ Verify ALB sticky sessions enabled
3. 🔄 Update ASG configuration
4. 🔄 Test with 2 instances first
5. 🔄 Monitor and adjust thresholds