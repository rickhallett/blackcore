# /pr - Pull Request Creation Assistant

You are now in PR creation mode. Create comprehensive, well-documented pull requests.

## PR Creation Process

### 1. Analyze Changes
- Review all commits since branching
- Identify key changes and their impact
- Group related changes logically
- Check for breaking changes

### 2. PR Title Format

Follow semantic format:
```
<type>(<scope>): <description>

Types: feat|fix|docs|style|refactor|perf|test|build|ci|chore
```

Examples:
- `feat(auth): add OAuth2 integration`
- `fix(api): resolve race condition in payment processing`
- `refactor(core): simplify event handling logic`

### 3. PR Description Template

```markdown
## Summary
Brief description of what this PR does and why.

## Changes
- [ ] Change 1 with explanation
- [ ] Change 2 with explanation
- [ ] Change 3 with explanation

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Test coverage maintained/improved

## Checklist
- [ ] My code follows the project style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Additional Context
[Any additional information that reviewers should know]

## Related Issues
Closes #[issue number]
Relates to #[issue number]
```

### 4. Pre-PR Checklist

Before creating the PR:

1. **Code Quality**
   - Run linters and fix issues
   - Ensure consistent formatting
   - Remove debug code and console logs
   - Update or remove TODO comments

2. **Testing**
   - All tests pass
   - New tests for new features
   - Edge cases covered
   - No reduction in coverage

3. **Documentation**
   - API docs updated
   - README changes if needed
   - Inline comments for complex logic
   - CHANGELOG updated

4. **Review Readiness**
   - Commits are logical and atomic
   - Commit messages are clear
   - No unrelated changes
   - Branch is up to date with target

### 5. PR Size Guidelines

Keep PRs manageable:
- **Small**: < 100 lines (quick review)
- **Medium**: 100-500 lines (normal review)
- **Large**: 500-1000 lines (needs justification)
- **Too Large**: > 1000 lines (consider splitting)

### 6. Review Response Template

When responding to review comments:

```markdown
> Reviewer comment here

Thanks for the feedback! I've addressed this by:
- [Specific change made]
- [Why this approach]

Commit: [commit hash]
```

### 7. Merge Strategies

Recommend merge strategy based on history:
- **Squash**: For feature branches with messy history
- **Merge commit**: For preserving complete history
- **Rebase**: For linear history (if team practice)

## AI-Assisted PR Creation

When using this command, I will:

1. **Analyze all changes**:
   ```bash
   git diff target-branch...HEAD
   git log target-branch..HEAD
   ```

2. **Generate PR content**:
   - Summarize changes comprehensively
   - Identify breaking changes
   - Suggest reviewers based on code ownership
   - Link related issues automatically

3. **Pre-flight checks**:
   - Verify CI will pass
   - Check for merge conflicts
   - Validate against PR template
   - Suggest improvements

4. **Create PR**:
   ```bash
   gh pr create --title "..." --body "..." --base main
   ```

## Example Usage

```
User: /pr
Claude: I'll help you create a comprehensive PR. Let me analyze your changes...

Analyzing branch 'feature/oauth-integration' against 'main'...

Found 15 commits affecting 23 files:
- Added OAuth2 provider system
- Implemented Google authentication
- Updated user model for OAuth
- Added integration tests
- Updated documentation

Suggested PR:

Title: feat(auth): implement OAuth2 authentication system

Description:
## Summary
This PR adds OAuth2 authentication support to the application, starting with Google as the first provider. The implementation follows OAuth 2.0 standards and includes proper token management and security measures.

## Changes
- ✨ Add OAuth2 provider abstraction layer
- 🔧 Implement Google OAuth2 provider with PKCE flow
- 🔐 Add secure token storage and rotation
- 🧪 Complete test coverage for auth flows
- 📚 Update API documentation

[Full PR description continues...]

Would you like me to:
1. Create this PR
2. Edit the description
3. Run additional checks
4. Split into multiple PRs
```

## PR Best Practices

1. **One PR = One Purpose**: Don't mix features with refactoring
2. **Description > Code**: Good description saves review time
3. **Screenshots**: Include for any UI changes
4. **Draft PRs**: Use for early feedback
5. **Review your own PR**: Catch issues before reviewers
6. **Respond promptly**: Keep momentum in reviews
7. **Update frequently**: Keep PR current with base branch

Remember: A well-crafted PR respects reviewers' time and gets merged faster!