package api

import (
	"context"
	"encoding/json"
	"fmt"
)

// GetShareStatus returns sharing settings and collaborators for a notebook.
func (c *Client) GetShareStatus(ctx context.Context, notebookID string) (map[string]any, error) {
	params := []any{notebookID}
	sourcePath := NotebookPath(notebookID)

	raw, err := c.Execute(ctx, RPCGetShareStatus, params, sourcePath)
	if err != nil {
		return nil, fmt.Errorf("getting share status: %w", err)
	}

	result := map[string]any{
		"notebook_id": notebookID,
		"is_public":   false,
	}

	outer, _ := ParseRawArray(raw)
	var collaborators []map[string]any

	if len(outer) > 0 {
		// Parse access level
		accessArr, _ := ParseRawArray(outer[0])
		if len(accessArr) > 0 {
			accessLevel := GetInt(accessArr[0])
			result["is_public"] = accessLevel == 1
		}
	}
	if len(outer) > 1 {
		// Parse collaborators
		collabArr, _ := ParseRawArray(outer[1])
		for _, c := range collabArr {
			collab := parseCollaborator(c)
			if collab != nil {
				collaborators = append(collaborators, collab)
			}
		}
	}

	result["collaborators"] = collaborators
	return result, nil
}

func parseCollaborator(data json.RawMessage) map[string]any {
	arr, err := ParseRawArray(data)
	if err != nil || len(arr) < 2 {
		return nil
	}
	email := GetString(arr[0])
	if email == "" {
		return nil
	}
	role := "viewer"
	if len(arr) > 1 {
		roleCode := GetInt(arr[1])
		switch roleCode {
		case 1:
			role = "owner"
		case 2:
			role = "editor"
		case 3:
			role = "viewer"
		}
	}
	return map[string]any{"email": email, "role": role}
}

// SetSharePublic enables or disables public link access.
func (c *Client) SetSharePublic(ctx context.Context, notebookID string, isPublic bool) error {
	accessLevel := 0 // restricted
	if isPublic {
		accessLevel = 1
	}

	params := []any{notebookID, accessLevel}
	sourcePath := NotebookPath(notebookID)

	_, err := c.Execute(ctx, RPCSetSharing, params, sourcePath)
	if err != nil {
		return fmt.Errorf("setting share access: %w", err)
	}
	return nil
}

// InviteCollaborator invites a user by email with a given role.
func (c *Client) InviteCollaborator(ctx context.Context, notebookID, email, role string) error {
	roleCode := 3 // viewer
	if role == "editor" {
		roleCode = 2
	}

	params := []any{notebookID, nil, []any{[]any{email, roleCode}}}
	sourcePath := NotebookPath(notebookID)

	_, err := c.Execute(ctx, RPCSetSharing, params, sourcePath)
	if err != nil {
		return fmt.Errorf("inviting collaborator: %w", err)
	}
	return nil
}
