{{/*
Name of this particular launchpad instance
*/}}
{{- define "launchpad.name" -}}
{{- printf "launchpad-%s" .Values.apolo_app_id | trunc 63 | trimSuffix "-" }}
{{- end }}


{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "launchpad.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "launchpad.labels" -}}
application: {{ .Values.labels.application }}
helm.sh/chart: {{ include "launchpad.chart" . }}
app.kubernetes.io/name: {{ include "launchpad.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Values.apolo_app_id }}
platform.apolo.us/app-id: {{ .Values.apolo_app_id | quote }}
{{- end }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "launchpad.selectorLabels" -}}
app.kubernetes.io/name: {{ include "launchpad.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
service: launchpad
{{- end }}

{{- define "launchpad.apoloPodLabels" -}}
platform.apolo.us/preset: {{ .Values.preset_name }}
platform.apolo.us/component: app
{{- end }}

{{- define "launchpad.domain" -}}
{{- printf "%s.%s" (include "launchpad.name" .) .Values.domain }}
{{- end }}

{{- define "launchpad.apiDomain" -}}
{{- printf "%s-api.%s" (include "launchpad.name" .) .Values.domain }}
{{- end }}

{{- define "launchpad.apiDomainWithProtocol" -}}
{{- printf "https://%s-api.%s" (include "launchpad.name" .) .Values.domain }}
{{- end }}

{{- define "keycloak.domain" -}}
{{- printf "%s-keycloak.%s" (include "launchpad.name" .) .Values.domain }}
{{- end }}

{{- define "launchpad.domainWithProtocol" -}}
{{- printf "https://%s.%s" (include "launchpad.name" .) .Values.domain }}
{{- end }}

{{- define "launchpad.admin-secret" -}}
{{- printf "%s-admin-secret" (include "launchpad.name" .) }}
{{- end }}
