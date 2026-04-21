import * as github from '@actions/github';
import * as core from '@actions/core';
import { Report } from './analyzer';

export async function reportHallucinations(
  token: string,
  reports: Report[],
  thresholdSeverity: string,
  failOnHallucination: boolean
): Promise<void> {
  const octokit = github.getOctokit(token);
  const context = github.context;
  const pullRequest = context.payload.pull_request;

  if (!pullRequest) {
    core.info('Not running in a Pull Request context. Skipping PR comments.');
    checkThresholdAndFail(reports, thresholdSeverity, failOnHallucination);
    return;
  }

  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const prNumber = pullRequest.number;
  const commitId = pullRequest.head.sha;

  let hasThresholdViolations = false;
  let totalIssues = 0;

  for (const report of reports) {
    if (report.error) {
      core.warning(`HalluGuard failed on ${report.file}: ${report.error}`);
      continue;
    }

    if (!report.hallucinations || report.hallucinations.length === 0) {
      continue; // No issues
    }

    for (const issue of report.hallucinations) {
      totalIssues++;
      if (isSeverityThresholdMet(issue.severity, thresholdSeverity)) {
        hasThresholdViolations = true;
      }

      const body = buildCommentBody(issue);
      const line = Math.max(issue.line, 1); // Ensure at least line 1

      try {
        await octokit.rest.pulls.createReviewComment({
          owner,
          repo,
          pull_number: prNumber,
          commit_id: commitId,
          path: report.file,
          line: line,
          side: 'RIGHT',
          body: body,
        });
      } catch (err: any) {
        // Octokit might fail if the line wasn't part of the PR diff
        core.warning(`Could not post comment on ${report.file}:${line} - ${err.message}`);
      }
    }
  }

  if (hasThresholdViolations && failOnHallucination) {
    core.setFailed(`HalluGuard: Found ${totalIssues} hallucination(s) meeting or exceeding the threshold (${thresholdSeverity}).`);
  } else if (totalIssues > 0) {
    core.warning(`HalluGuard: Found ${totalIssues} hallucination(s).`);
  } else {
    core.info('HalluGuard: Clean. No hallucinations detected.');
  }
}

function buildCommentBody(issue: any): string {
  const suggestionTxt = issue.suggestion ? `\n\n**Suggestion:** \`${issue.suggestion}\`` : '';
  
  let severityEmoji = 'ℹ️';
  if (issue.severity === 'CRITICAL' || issue.severity === 'HIGH') severityEmoji = '🚨';
  if (issue.severity === 'MEDIUM') severityEmoji = '⚠️';

  return `### ${severityEmoji} HalluGuard AI: ${issue.type}
  
**Token:** \`${issue.token}\`
**Severity:** ${issue.severity}

${issue.explanation}${suggestionTxt}`;
}

const SEVERITY_LEVELS: Record<string, number> = {
  LOW: 1,
  MEDIUM: 2,
  HIGH: 3,
  CRITICAL: 4
};

function isSeverityThresholdMet(severity: string, threshold: string): boolean {
  const sevVal = SEVERITY_LEVELS[severity.toUpperCase()] || 0;
  const threshVal = SEVERITY_LEVELS[threshold.toUpperCase()] || 2;
  return sevVal >= threshVal;
}

function checkThresholdAndFail(
  reports: Report[],
  thresholdSeverity: string,
  failOnHallucination: boolean
): void {
  let hasThresholdViolations = false;
  let totalIssues = 0;

  for (const report of reports) {
    for (const issue of report.hallucinations || []) {
      totalIssues++;
      if (isSeverityThresholdMet(issue.severity, thresholdSeverity)) {
        hasThresholdViolations = true;
      }
    }
  }

  if (hasThresholdViolations && failOnHallucination) {
    core.setFailed(`HalluGuard: Found ${totalIssues} hallucination(s) meeting the threshold (${thresholdSeverity}).`);
  }
}
