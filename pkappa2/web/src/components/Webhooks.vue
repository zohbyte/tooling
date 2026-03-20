<template>
  <div>
    <ToolBar>
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-btn icon v-bind="props" @click="refresh">
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </template>
        <span>Refresh</span>
      </v-tooltip>
      <v-dialog v-model="addDialogVisible" width="500" @keydown.enter="add">
        <template #default>
          <v-form>
            <v-card>
              <v-card-title class="text-h5">
                Add Webhook Endpoint
              </v-card-title>
              <v-card-text>
                Add the address of the Webhook endpoint to connect to.

                <v-text-field
                  v-model="newAddress"
                  label="Address"
                  autofocus
                ></v-text-field>
              </v-card-text>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn variant="text" @click="addDialogVisible = false"
                  >Cancel</v-btn
                >
                <v-btn
                  variant="text"
                  :disabled="addDialogLoading"
                  :loading="addDialogLoading"
                  :color="addDialogError ? 'error' : 'primary'"
                  type="submit"
                  @click="add"
                  >Add</v-btn
                >
              </v-card-actions>
            </v-card>
          </v-form>
        </template>
        <template #activator="{ props: propsDialog }">
          <v-tooltip location="bottom">
            <template #activator="{ props: propsTooltip }">
              <v-btn v-bind="{ ...propsDialog, ...propsTooltip }" icon>
                <v-icon>mdi-plus</v-icon>
              </v-btn>
            </template>
            <span>Add Endpoint</span>
          </v-tooltip>
        </template>
      </v-dialog>
    </ToolBar>

    <!-- PCAP Processor Webhooks -->
    <v-card density="compact" variant="flat">
      <v-card-title>Webhook Endpoints</v-card-title>
      <v-card-text>
        All URIs that are registered as Webhook endpoints will be notified when
        a new PCAP file was processed. The Webhook endpoints will receive a POST
        request with a JSON body containing an array of strings with the
        absolute paths of the processed PCAP files.
      </v-card-text>
    </v-card>
    <v-data-table
      :headers="headers"
      :items="store.webhooks || []"
      density="compact"
      disable-pagination
      disable-filtering
      hide-default-footer
      hover
    >
      <template #[`item.address`]="{ item }">
        {{ item }}
      </template>
      <template #[`item.delete`]="{ item }">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn
              variant="plain"
              density="compact"
              icon
              v-bind="props"
              @click="
                delDialogAddress = item;
                delDialogVisible = true;
              "
            >
              <v-icon>mdi-delete</v-icon></v-btn
            >
          </template>
          <span>Delete</span>
        </v-tooltip>
      </template>
    </v-data-table>
    <v-dialog v-model="delDialogVisible" width="500" @keydown.enter="del">
      <template #default
        ><v-form>
          <v-card>
            <v-card-title class="text-h5">
              Confirm Webhook endpoint deletion
            </v-card-title>
            <v-card-text>
              Do you want to delete the Webhook endpoint
              <code>{{ delDialogAddress }}</code
              >?
            </v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn variant="text" @click="delDialogVisible = false">No</v-btn>
              <v-btn
                variant="text"
                :disabled="delDialogLoading"
                :loading="delDialogLoading"
                :color="delDialogError ? 'error' : 'primary'"
                @click="del"
                >Yes</v-btn
              >
            </v-card-actions>
          </v-card>
        </v-form>
      </template>
    </v-dialog>

    <!-- Discord Flag Alert Webhooks -->
    <v-divider class="my-4"></v-divider>

    <v-card density="compact" variant="flat">
      <v-card-title>
        <v-icon class="mr-2" color="indigo">mdi-discord</v-icon>
        Discord Flag Alert Webhooks
      </v-card-title>
      <v-card-text>
        Discord webhook URLs registered here will receive a notification
        whenever a tag whose name contains <strong>"flag"</strong> gets new
        matching streams after a PCAP is analyzed. This alerts you when flags
        may be going out. Use Discord's
        <em>Server Settings → Integrations → Webhooks</em> to create a webhook
        URL.
      </v-card-text>
    </v-card>

    <v-toolbar density="compact" flat>
      <v-spacer></v-spacer>
      <v-dialog
        v-model="discordAddDialogVisible"
        width="500"
        @keydown.enter="discordAdd"
      >
        <template #default>
          <v-form>
            <v-card>
              <v-card-title class="text-h5">
                Add Discord Webhook URL
              </v-card-title>
              <v-card-text>
                Paste your Discord webhook URL below.

                <v-text-field
                  v-model="discordNewAddress"
                  label="Discord Webhook URL"
                  autofocus
                  placeholder="https://discord.com/api/webhooks/..."
                ></v-text-field>
              </v-card-text>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn
                  variant="text"
                  @click="discordAddDialogVisible = false"
                  >Cancel</v-btn
                >
                <v-btn
                  variant="text"
                  :disabled="discordAddDialogLoading"
                  :loading="discordAddDialogLoading"
                  :color="discordAddDialogError ? 'error' : 'primary'"
                  type="submit"
                  @click="discordAdd"
                  >Add</v-btn
                >
              </v-card-actions>
            </v-card>
          </v-form>
        </template>
        <template #activator="{ props: propsDialog }">
          <v-tooltip location="bottom">
            <template #activator="{ props: propsTooltip }">
              <v-btn v-bind="{ ...propsDialog, ...propsTooltip }" icon>
                <v-icon>mdi-plus</v-icon>
              </v-btn>
            </template>
            <span>Add Discord Webhook</span>
          </v-tooltip>
        </template>
      </v-dialog>
    </v-toolbar>

    <v-data-table
      :headers="discordHeaders"
      :items="store.discordWebhooks || []"
      density="compact"
      disable-pagination
      disable-filtering
      hide-default-footer
      hover
    >
      <template #[`item.address`]="{ item }">
        {{ item }}
      </template>
      <template #[`item.delete`]="{ item }">
        <v-tooltip location="bottom">
          <template #activator="{ props }">
            <v-btn
              variant="plain"
              density="compact"
              icon
              v-bind="props"
              @click="
                discordDelDialogAddress = item;
                discordDelDialogVisible = true;
              "
            >
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
          <span>Delete</span>
        </v-tooltip>
      </template>
    </v-data-table>

    <v-dialog
      v-model="discordDelDialogVisible"
      width="500"
      @keydown.enter="discordDel"
    >
      <template #default>
        <v-form>
          <v-card>
            <v-card-title class="text-h5">
              Confirm Discord Webhook deletion
            </v-card-title>
            <v-card-text>
              Do you want to delete the Discord Webhook URL
              <code>{{ discordDelDialogAddress }}</code>?
            </v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn variant="text" @click="discordDelDialogVisible = false"
                >No</v-btn
              >
              <v-btn
                variant="text"
                :disabled="discordDelDialogLoading"
                :loading="discordDelDialogLoading"
                :color="discordDelDialogError ? 'error' : 'primary'"
                @click="discordDel"
                >Yes</v-btn
              >
            </v-card-actions>
          </v-card>
        </v-form>
      </template>
    </v-dialog>

    <!-- Discord Message Template -->
    <v-divider class="my-4"></v-divider>

    <v-card density="compact" variant="flat">
      <v-card-title>
        <v-icon class="mr-2" color="indigo">mdi-message-cog</v-icon>
        Discord Alert Message Template
      </v-card-title>
      <v-card-text>
        Customise the embed message that gets sent to Discord when a flag tag
        fires. Use the following placeholders anywhere in the title or
        description:
        <v-table density="compact" class="mt-2 mb-4" style="max-width: 480px">
          <thead>
            <tr>
              <th>Placeholder</th>
              <th>Replaced with</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>{tag}</code></td>
              <td>The tag name that matched (e.g. <em>tag/flag-outgoing</em>)</td>
            </tr>
            <tr>
              <td><code>{count}</code></td>
              <td>Number of <strong>new</strong> streams matched in this PCAP</td>
            </tr>
            <tr>
              <td><code>{time}</code></td>
              <td>UTC timestamp when the alert fired (e.g. <em>2026-03-01 14:05:00 UTC</em>)</td>
            </tr>
          </tbody>
        </v-table>

        <v-form @submit.prevent="saveTemplate">
          <v-text-field
            v-model="templateTitle"
            label="Embed Title"
            density="compact"
            class="mb-2"
          ></v-text-field>
          <v-textarea
            v-model="templateDescription"
            label="Embed Description"
            density="compact"
            rows="3"
            auto-grow
            class="mb-2"
          ></v-textarea>
          <v-text-field
            v-model="templateColor"
            label="Embed Colour (hex, e.g. #FF0000)"
            density="compact"
            :rules="[validateColor]"
            class="mb-2"
            style="max-width: 260px"
          >
            <template #prepend-inner>
              <span
                :style="{
                  display: 'inline-block',
                  width: '18px',
                  height: '18px',
                  borderRadius: '3px',
                  background: colorPreview,
                  border: '1px solid rgba(0,0,0,.3)',
                  marginRight: '4px',
                }"
              ></span>
            </template>
          </v-text-field>

          <!-- Discord user pings -->
          <div class="mb-3">
            <div class="text-subtitle-2 mb-1">
              Ping Users
              <span class="text-caption text-medium-emphasis ml-1">
                — these Discord user IDs will be @mentioned above the embed
              </span>
            </div>
            <div class="d-flex flex-wrap ga-2 mb-2">
              <v-chip
                v-for="(uid, idx) in templateMentionUserIDs"
                :key="uid"
                closable
                size="small"
                @click:close="templateMentionUserIDs.splice(idx, 1)"
              >
                {{ uid }}
              </v-chip>
              <span
                v-if="templateMentionUserIDs.length === 0"
                class="text-caption text-medium-emphasis"
              >
                No users added yet
              </span>
            </div>
            <div class="d-flex align-center" style="gap: 8px; max-width: 420px">
              <v-text-field
                v-model="newMentionUserID"
                label="Discord User ID"
                density="compact"
                hide-details
                placeholder="e.g. 123456789012345678"
                @keydown.enter.prevent="addMentionUserID"
              ></v-text-field>
              <v-btn
                icon
                size="small"
                variant="tonal"
                :disabled="!newMentionUserID.trim()"
                @click="addMentionUserID"
              >
                <v-icon>mdi-plus</v-icon>
              </v-btn>
            </div>
          </div>

          <v-card
            variant="outlined"
            class="mb-3"
            :style="{ borderLeft: `4px solid ${colorPreview}` }"
          >
            <v-card-subtitle class="pt-3 pb-0 font-weight-bold">
              Preview
            </v-card-subtitle>
            <v-card-text
              v-if="templateMentionUserIDs.length > 0"
              class="pt-1 pb-0 text-caption text-medium-emphasis"
            >
              {{ previewMentions }}
            </v-card-text>
            <v-card-title class="text-body-1 pt-1 font-weight-bold">
              {{ previewTitle }}
            </v-card-title>
            <v-card-text class="pt-0 text-body-2">
              {{ previewDescription }}
            </v-card-text>
          </v-card>

          <v-btn
            type="submit"
            color="primary"
            :loading="templateSaveLoading"
            :disabled="templateSaveLoading || !isColorValid"
            prepend-icon="mdi-content-save"
          >
            Save Template
          </v-btn>
          <v-btn
            variant="text"
            class="ml-2"
            @click="resetTemplate"
          >
            Reset to Defaults
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts" setup>
import { EventBus } from "./EventBus";
import { ref, computed, onMounted, watch } from "vue";
import { useRootStore } from "@/stores";

// --- PCAP Processor Webhook state ---
const delDialogVisible = ref(false);
const delDialogAddress = ref("");
const delDialogLoading = ref(false);
const delDialogError = ref(false);

const addDialogVisible = ref(false);
const addDialogLoading = ref(false);
const addDialogError = ref(false);
const newAddress = ref("");

// --- Discord Flag Alert Webhook state ---
const discordAddDialogVisible = ref(false);
const discordAddDialogLoading = ref(false);
const discordAddDialogError = ref(false);
const discordNewAddress = ref("");

const discordDelDialogVisible = ref(false);
const discordDelDialogAddress = ref("");
const discordDelDialogLoading = ref(false);
const discordDelDialogError = ref(false);

const store = useRootStore();

const headers = [
  { title: "Address", value: "address", cellClass: "cursor-pointer" },
  { title: "", value: "delete", sortable: false, cellClass: "cursor-pointer" },
];

const discordHeaders = [
  { title: "Discord Webhook URL", value: "address", cellClass: "cursor-pointer" },
  { title: "", value: "delete", sortable: false, cellClass: "cursor-pointer" },
];

// --- Discord Message Template state ---
const DEFAULT_TITLE = "⚠️ Flag Alert: Possible Flag Exfiltration Detected";
const DEFAULT_DESCRIPTION =
  "Tag **`{tag}`** matched **{count}** new stream(s) in the latest PCAP analysis at {time}. Flags may be going out!";
const DEFAULT_COLOR = "#FF0000";

const templateTitle = ref(DEFAULT_TITLE);
const templateDescription = ref(DEFAULT_DESCRIPTION);
const templateColor = ref(DEFAULT_COLOR);
const templateMentionUserIDs = ref<string[]>([]);
const newMentionUserID = ref("");
const templateSaveLoading = ref(false);

function addMentionUserID() {
  const id = newMentionUserID.value.trim();
  if (!id) return;
  if (!templateMentionUserIDs.value.includes(id)) {
    templateMentionUserIDs.value.push(id);
  }
  newMentionUserID.value = "";
}

// Sync local fields when the store loads the template
watch(
  () => store.discordWebhookTemplate,
  (tmpl) => {
    if (tmpl) {
      templateTitle.value = tmpl.Title;
      templateDescription.value = tmpl.Description;
      templateColor.value = tmpl.Color;
      templateMentionUserIDs.value = tmpl.MentionUserIDs ?? [];
    }
  },
  { immediate: true },
);

const HEX_RE = /^#[0-9a-fA-F]{6}$/;
const isColorValid = computed(() => HEX_RE.test(templateColor.value));

function validateColor(v: string) {
  return HEX_RE.test(v) || "Must be a hex colour like #FF0000";
}

const colorPreview = computed(() =>
  isColorValid.value ? templateColor.value : "#cccccc",
);

/** Replace template placeholders with example values for the live preview. */
function applyPlaceholders(s: string) {
  return s
    .replace(/\{tag\}/g, "tag/flag-outgoing")
    .replace(/\{count\}/g, "3")
    .replace(/\{time\}/g, "2026-03-01 14:05:00 UTC");
}

const previewTitle = computed(() => applyPlaceholders(templateTitle.value));
const previewDescription = computed(() =>
  applyPlaceholders(templateDescription.value),
);
const previewMentions = computed(() =>
  templateMentionUserIDs.value.map((id) => `@${id}`).join(" "),
);

function saveTemplate() {
  if (!isColorValid.value) return;
  templateSaveLoading.value = true;
  store
    .saveDiscordWebhookTemplate({
      Title: templateTitle.value,
      Description: templateDescription.value,
      Color: templateColor.value,
      MentionUserIDs: templateMentionUserIDs.value,
    })
    .then(() => {
      templateSaveLoading.value = false;
    })
    .catch((err: Error) => {
      templateSaveLoading.value = false;
      EventBus.emit(
        "showError",
        `Failed to save Discord message template: ${err.message}`,
      );
    });
}

function resetTemplate() {
  templateTitle.value = DEFAULT_TITLE;
  templateDescription.value = DEFAULT_DESCRIPTION;
  templateColor.value = DEFAULT_COLOR;
  templateMentionUserIDs.value = [];
  saveTemplate();
}

onMounted(() => {
  refresh();
});

function refresh() {
  store.updateWebhooks().catch((err: Error) => {
    EventBus.emit(
      "showError",
      `Failed to update registered webhooks: ${err.message}`,
    );
  });
  store.updateDiscordWebhooks().catch((err: Error) => {
    EventBus.emit(
      "showError",
      `Failed to update Discord webhooks: ${err.message}`,
    );
  });
  store.fetchDiscordWebhookTemplate().catch((err: Error) => {
    EventBus.emit(
      "showError",
      `Failed to load Discord message template: ${err.message}`,
    );
  });
}

// --- PCAP Processor Webhook actions ---
function add() {
  addDialogLoading.value = true;
  addDialogError.value = false;
  store
    .addWebhook(newAddress.value)
    .then(() => {
      addDialogVisible.value = false;
      addDialogLoading.value = false;
      newAddress.value = "";
      refresh();
    })
    .catch((err: Error) => {
      addDialogLoading.value = false;
      addDialogError.value = true;
      EventBus.emit(
        "showError",
        `Failed to add webhook endpoint: ${err.message}`,
      );
    });
}

function del() {
  delDialogLoading.value = true;
  delDialogError.value = false;
  store
    .delWebhook(delDialogAddress.value)
    .then(() => {
      delDialogVisible.value = false;
      delDialogLoading.value = false;
      refresh();
    })
    .catch((err: Error) => {
      EventBus.emit(
        "showError",
        `Failed to delete webhook endpoint: ${err.message}`,
      );
      delDialogError.value = true;
      delDialogLoading.value = false;
    });
}

// --- Discord Flag Alert Webhook actions ---
function discordAdd() {
  discordAddDialogLoading.value = true;
  discordAddDialogError.value = false;
  store
    .addDiscordWebhook(discordNewAddress.value)
    .then(() => {
      discordAddDialogVisible.value = false;
      discordAddDialogLoading.value = false;
      discordNewAddress.value = "";
      refresh();
    })
    .catch((err: Error) => {
      discordAddDialogLoading.value = false;
      discordAddDialogError.value = true;
      EventBus.emit(
        "showError",
        `Failed to add Discord webhook: ${err.message}`,
      );
    });
}

function discordDel() {
  discordDelDialogLoading.value = true;
  discordDelDialogError.value = false;
  store
    .delDiscordWebhook(discordDelDialogAddress.value)
    .then(() => {
      discordDelDialogVisible.value = false;
      discordDelDialogLoading.value = false;
      refresh();
    })
    .catch((err: Error) => {
      EventBus.emit(
        "showError",
        `Failed to delete Discord webhook: ${err.message}`,
      );
      discordDelDialogError.value = true;
      discordDelDialogLoading.value = false;
    });
}
</script>
<style lang="css">
.cursor-pointer {
  cursor: pointer;
}
</style>
