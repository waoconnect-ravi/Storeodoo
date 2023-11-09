
from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError
import paramiko


class SftpSyncing(models.Model):
    _name = "sftp.syncing"

    name = fields.Char("Server name", required=True)
    sftp_host = fields.Char("Host", required=True)
    sftp_username = fields.Char("User Name", required=True)
    sftp_password = fields.Char("Password")
    sftp_port = fields.Char("Port", required=True)
    store = fields.Selection([('', '')], string="Store")
    cron_created = fields.Boolean(string="Cron Created", default=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    active = fields.Boolean('Active', default=True)

    def connect_sftp(self):
        try:
            sftp_host = self.sftp_host
            sftp_username = self.sftp_username
            sftp_password = self.sftp_password
            sftp_port = int(self.sftp_port)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=sftp_host, username=sftp_username,
                        password=sftp_password, port=sftp_port or 2222)
            sftp_client = ssh.open_sftp()
            return sftp_client
        except Exception as e:
            raise UserError(
                _("SFTP Connection Test Failed! Here is what we got instead:\n %s") % (e))

    def sftp_test_connection(self):
        try:
            sftp_client = self.connect_sftp()
            if sftp_client:
                title = _("SFTP Connection Test Succeeded!")
                message = _("Everything seems properly set up!")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': title,
                        'message': message,
                        'sticky': False,
                    }
                }
        except Exception as e:
            raise UserError(
                _("Connection Failed! Here is what we got instead:\n %s") % (e))

    def rename_file_from_sftp_server(self, sftp_client, old_path, new_path):
        # You can use this method to change file location as well
        try:
            sftp_client.rename(old_path, new_path)
        except Exception as e:
            raise UserError(
                _("Error while change file location! Here is what we got instead:\n %s") % (e))

    def export_file_to_sftp_server(self, sftp_client, local_location, server_location):
        try:
            sftp_client.put(local_location, server_location)
        except Exception as e:
            raise UserError(
                _("Error while export file to Server! Here is what we got instead:\n %s") % (e))

    def import_file_to_local_from_sftp(self, sftp_client, server_location, local_location):
        try:
            sftp_client.get(server_location, local_location)
        except Exception as e:
            raise UserError(
                _("Error while getting file from Server! Here is what we got instead:\n %s") % (e))

    def get_all_files_and_folders_from_server_location(self, sftp_client, server_location, match):
        try:
            sftp_client.chdir(server_location)
            return list(set([x for x in sftp_client.listdir() if match in x]))
        except Exception as e:
            raise UserError(
                _("Error while get file and folders name from Server! Here is what we got instead:\n %s") % (e))

    def create_cron_job(self, cron_name, code_method, interval_number=10, interval_type='minutes', numbercall=1):
        self.env['ir.cron'].create({
            'name': cron_name,
            'model_id': self.env.ref('sftp_server_connector.model_sftp_syncing').id,
            'state': 'code',
            'code': code_method,
            'interval_number': interval_number,
            'interval_type': interval_type,
            'numbercall': numbercall,
            'doall': True,
            'active': True,
            'user_id': 1
        })

    def click_to_create_cron(self):
        if not self.store:
            raise ValidationError(_("PLease Select Your 3PL store."))
        if hasattr(self, '{}_create_schedule_actions'.format(self.store)):
            getattr(self, '{}_create_schedule_actions'.format(self.store))()
        self.cron_created = True
